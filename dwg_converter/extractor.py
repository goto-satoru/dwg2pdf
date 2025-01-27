import logging
import sys
import arrow
import os
import subprocess
import pandas as pd
from threading import Event
from cognite.client import CogniteClient
from cognite.client.data_classes import ExtractionPipelineRun
from cognite.extractorutils.statestore import AbstractStateStore
from cognite.client.data_classes.data_modeling.cdm.v1 import CogniteFileApply, CogniteFile
from dwg_converter.config import Config
from dwg_converter import __version__

MAX_DWG_FILES = None

logger = logging.getLogger(__name__)


def report_run(config: Config, client: CogniteClient, status: str, message: str) -> None:
    try:
        if config.cognite.extraction_pipeline.external_id:
            logger.info(
                f"Extraction Pipeline External ID: '{config.cognite.extraction_pipeline.external_id}'"
            )
            client.extraction_pipelines.runs.create(
                ExtractionPipelineRun(
                    extpipe_external_id=config.cognite.extraction_pipeline.external_id,
                    status=status,
                    message=message,
                )
            )
            logger.info(f"Reporting new {status} run: {message}")
    except Exception:
        logger.exception("Error while reporting run")


def delete_files(tmp_dir, logger):
    logger.info(f"Remove tempory DWG/PDF files in '{tmp_dir}' directory")
    for filename in os.listdir(tmp_dir):
        try:
            os.remove(f"{tmp_dir}/{filename}")
        except Exception as e:
            logger.error(f"Failed to delete {tmp_dir}{filename}. Reason: {e}")
        if filename.endswith(".dwg") or filename.endswith(".pdf"):
            file_path = os.path.join(tmp_dir, filename)
            try:
                os.remove(file_path)
                logger.info(f"Deleted file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete {file_path} - {e}")


def dwg2pdf(config: Config, client: CogniteClient, dwg_filename: str, instance_id, meta_cdm, logger):
    logger.info(f"  DWG instance_id: {instance_id}")
    # tags = meta_cdm.tags
    # logger.info(f"  tags: {tags}")

    base_name = os.path.splitext(dwg_filename)[0]
    pdf_filename = f"{base_name}.pdf"

    # download the DWG file
    client.files.download(directory=config.dwg.tmp_dir, instance_id=instance_id)

    # DWG -> PDF using QCAD Pro dwg2pdf
    input_file = os.path.join(config.dwg.tmp_dir, dwg_filename)
    output_file = os.path.join(config.dwg.tmp_dir, f"{base_name}.pdf")
    logger.info(f"  Convert DWG -> PDF")
    try:
        if sys.platform == 'win32':
            dwg2pdf_path = 'C:\Program Files\QCAD\dwg2pdf.bat'
        else:
            dwg2pdf_path = '/Applications/QCAD-Pro.app/Contents/Resources/dwg2pdf'

        commands = [dwg2pdf_path] + config.dwg.dwg2pdf_args + [input_file]
        logger.debug(f"  DWG2PDF command: {commands}")
        subprocess.run(commands, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        logger.info(f"  *** Failed to convert {base_name}.dwg", file=sys.stderr)
        return None

    # copy metadata of PDF on CDM
    space = instance_id.space
    xid_dwg = instance_id.external_id
    xid = f"pdf:{xid_dwg}"
    tags = ['dwg2pdf']              # original tags should be None !!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    logger.info(f"  tags: {tags}")
    # tags = list(set(tags))
    file = CogniteFileApply(
        space=space,
        external_id=xid,
        name=f"{base_name}.pdf",
        mime_type="application/pdf",
        directory=meta_cdm.directory,
        tags=tags
    )
    instance_id_pdf = file.as_id()
    try:
        created = client.data_modeling.instances.apply(file)
        # logger.info(f"  metadata: {created}")
    except Exception as e:
        logger.error(f"  *** Failed to upsert CogniteFile instance: {e}")

    logger.info(f"  PDF instance_id: {instance_id_pdf}")

    # upload the PDF file
    try:
        response = client.files.upload_content(
            instance_id=instance_id_pdf,
            path=output_file
        )
        # os.remove(input_file)
        # os.remove(output_file)
    except Exception as e:
        logger.info(f"  Failed to upload {output_file} - {e}")

    # update DWG tags -> ['dwg2pdf]'
    dwg_file = CogniteFileApply(
        space=space,
        external_id=meta_cdm.external_id,
        name=meta_cdm.name,
        mime_type=meta_cdm.mime_type,
        directory=meta_cdm.directory,
        tags=tags                         #  !!!!!!
    )
    try:
        created = client.data_modeling.instances.apply(dwg_file)
    except Exception as e:
        logger.error(f"  *** Failed to upsert DWG CogniteFile instance: {e}")

    return output_file


def run_extractor(cognite: CogniteClient, states: AbstractStateStore, config: Config, stop_event: Event) -> None:
    start_time = arrow.now()
    client = config.cognite.get_cognite_client("dwg-converter")
    report_run(config, client, "success", f"DWG Converter v{__version__}")

    logger.info("--------------------------------------------------------------------------------")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"CDF project: {config.cognite.project}")
    logger.info("--------------------------------------------------------------------------------")
    logger.info(f"DWG2PDF arguments: {config.dwg.dwg2pdf_args}")
    logger.info(f"config.dwg.tmp_dir: {config.dwg.tmp_dir}")

    # -------------------------------------------------------------------
    tmp_dir = config.dwg.tmp_dir
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
    else:
        delete_files(tmp_dir, logger)

    prev_run_time = states.get_state(external_id="previous_conversion")[1] or 0
    logger.info(f"Previous run: {prev_run_time}")
    prev_run = int(arrow.get(prev_run_time).timestamp()*1000)

    # list DWG files
    dwg_files = client.files.list(
        limit=MAX_DWG_FILES,
        mime_type="image/vnd.dwg",
        uploaded_time={"min": prev_run}
    )

    # convert and upload to CogniteFile
    count = 0
    converted_dwgs = []
    for dwg in dwg_files:
        meta_cdm = client.data_modeling.instances.retrieve_nodes(
            nodes=dwg.instance_id, node_cls=CogniteFile
        )
        # print(meta_cdm)
        if meta_cdm is None:
            logger.info(f"*** CogniteFile property is None: {dwg.name}")
            continue
        tags = meta_cdm.tags
        # if tags is not None:
        #     logger.info(f"*** Already converted: {dwg.name}")
        #     continue
        count += 1
        logger.info(f"--- #{count} {dwg.name}")
        pdf_file = dwg2pdf(config, client, dwg.name, dwg.instance_id, meta_cdm, logger)
        directory = meta_cdm.directory
        space = dwg.instance_id.space
        external_id = dwg.instance_id.external_id
        converted_at = arrow.now().to('+09:00').format("YYYY-MM-DDTHH:mm:ssZ")
        converted_dwgs.append((external_id, space, dwg.name, directory, converted_at))

    df_raw = pd.DataFrame(converted_dwgs, columns=['external_id', 'space', 'name', 'directory', 'converted_at'])
    df_raw.set_index('external_id', inplace=True)
    df_raw['pdf_external_id'] = df_raw.index.map(lambda external_id: f"pdf:{external_id}")
    # print(df_raw)
    client.raw.rows.insert_dataframe(config.dwg.raw_db, config.dwg.raw_table, df_raw, ensure_parent=True)
    report_run(config, client, "success", f"Converted {count} DWG files to PDF")

    delete_files(tmp_dir, logger)

    states.set_state(external_id="previous_conversion", high=start_time.to("+0900").format("YYYY-MM-DDTHH:mm:ssZ"))

    end_time = arrow.now()
    logger.info(f"Elapsed time: {end_time - start_time}")

from cognite.extractorutils import Extractor
from dwg_converter import __version__
from dwg_converter.extractor import run_extractor
from dwg_converter.config import Config


def main(config_file_path: str = "config.yml") -> None:
    with Extractor(
        name="dwg_converter",
        description="convert DWG into PDF",
        config_class=Config,
        config_file_path=config_file_path,
        run_handle=run_extractor,
        version=__version__,
    ) as extractor:
        extractor.run()


if __name__ == "__main__":
    main()

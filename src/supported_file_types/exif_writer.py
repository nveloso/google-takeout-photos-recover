from abc import abstractmethod


class ExifWriter:
    DATETIME_STR_FORMAT = '%Y:%m:%d %H:%M:%S'

    @staticmethod
    @abstractmethod
    def write(source_filepath: str, output_filepath: str, metadata: dict) -> None:
        """
        Copies the source_filepath file to output_filepath location and appends the EXIF metadata present in metadata
        argument.

        :param source_filepath: The source file, image or video
        :param output_filepath: The output folder for the image or video with recovered metadata
        :param metadata: EXIF metadata to write to the image or video
        :return: None
        """
        ...

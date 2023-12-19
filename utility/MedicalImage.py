import numpy as np
import SimpleITK as sitk


class MedicalImage:
    def __init__(self, image: sitk.Image, modality: str, channel: int = None):
        self.size = image.GetSize()
        self.spacing = image.GetSpacing()
        self.modality = modality  # PT, CT, NM, OT
        self.array = sitk.GetArrayFromImage(image)

        self.channel = (
            channel if channel is not None else 1 if len(self.array.shape) == len(self.size) else self.array.shape[-1]
        )
        assert self.channel == 1 or self.channel == 3, f"not support channel = {self.channel}."

        assert len(self.size) == 3, f"not support Medical Image's size = {str(self.size)}."

        self.array_norm = None
        self.normlize()

    def normlize(self, amin: float = None, amax: float = None):
        if self.channel == 1:
            if amin is None:
                amin = self.array.min()
            if amax is None:
                amax = self.array.max()
            _array = 1.0 * (self.array - amin) / (amax - amin)
            _array = np.clip((_array * 255).round(), 0, 255)
        else:
            _array = self.array
        self.array_norm = _array.astype(np.uint8)

    def plane_norm(self, view: str, pos: int):
        """
        get the normalized plane of Medical Image
        :param view: Sagittal, Coronal, Transverse
        :param pos: the position, range: [1, size]
        """
        if view == "s":
            return self.array_norm[:, :, pos - 1, ...]
        elif view == "c":
            return self.array_norm[:, pos - 1, ...]
        elif view == "t":
            return self.array_norm[pos - 1, ...]
        else:
            raise Exception(f"not support view = {view}.")

    def plane_origin(self, view: str, pos: int):
        """
        get the origin plane of Medical Image
        :param view: Sagittal, Coronal, Transverse
        :param pos: the position
        """
        if view == "s":
            return self.array[:, :, pos - 1, ...]
        elif view == "c":
            return self.array[:, pos - 1, ...]
        elif view == "t":
            return self.array[pos - 1, ...]
        else:
            raise Exception(f"not support view = {view}.")

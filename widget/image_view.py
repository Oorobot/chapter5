from typing import Union

import numpy as np
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QResizeEvent, QWheelEvent
from PyQt6.QtWidgets import QGraphicsView, QWidget

from utility import MedicalImage, MedicalImage2

from .image_item import ImageItem
from .image_item2 import ImageItem2
from .image_scene import ImageScene
from .message_box import warning


class ImageView(QGraphicsView):
    position_changed = pyqtSignal(int)

    def __init__(self, view: str, parent: QWidget = None):
        # 定义成员属性
        self.view = view
        self.image, self.label = None, None
        self.image_item, self.label_item = None, None
        self._position = self._position_max = {"s": 1, "c": 1, "t": 1}

        self.color_map = None

        self.scale_factor = 1.05
        self._scale_default = {"s": (1.0, 1.0), "c": (1.0, 1.0), "t": (1.0, 1.0)}

        self.resize_or_slide = False

        self.label_opacity = 0.50

        # 初始化
        super().__init__(parent)
        self._scene = ImageScene()
        self.setScene(self._scene)

        # 抗锯齿
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.TextAntialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        # 更新模式
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)

        # 隐藏滚动条
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # 设置拖动
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        # 设置缩放中心
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)

    @property
    def position(self):
        return self._position[self.view]

    @position.setter
    def position(self, p: int):
        self._position[self.view] = min(max(p, 1), self.position_max)

    @property
    def position_max(self):
        return self._position_max[self.view]

    @property
    def scale_default(self):
        return self._scale_default[self.view]

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self.resize_or_slide:
            if event.angleDelta().y() > 0:
                factor = self.scale_factor
            else:
                factor = 1 / self.scale_factor
            self.scale(factor, factor)
        else:
            if event.angleDelta().y() > 0:
                self.position += 1
            else:
                self.position -= 1
            # 位置信息改变
            self.position_changed.emit(self.position)
            self.set_current_plane()

    def reset(self) -> None:
        size_s, size_c, size_t = (s1 * s2 for s1, s2 in zip(self.image.size, self.image.spacing))
        _scale_s, _scale_c, _scale_t = (
            min(self.height() * 1.0 / size_t, self.width() * 1.0 / size_c),
            min(self.height() * 1.0 / size_t, self.width() * 1.0 / size_s),
            min(self.height() * 1.0 / size_c, self.width() * 1.0 / size_s),
        )
        self._scale_default = {
            "s": (self.image.spacing[1] * _scale_s, self.image.spacing[2] * _scale_s),
            "c": (self.image.spacing[0] * _scale_c, self.image.spacing[2] * _scale_c),
            "t": (self.image.spacing[0] * _scale_t, self.image.spacing[1] * _scale_t),
        }
        self.resetTransform()
        self.scale(*self.scale_default)  # x, y
        self.centerOn(0, 0)

    def resizeEvent(self, event: QResizeEvent) -> None:
        # scene 的大小随着 view 变化
        w, h = event.size().width(), event.size().height()
        self.scene().setSceneRect(-w * 10, -h * 10, w * 20, h * 20)

    # 切换视图
    def set_view(self, view: str):
        self.view = view
        self.reset()
        if self.image is not None:
            self.set_image_item(self.image.plane(self.view, self.position))
        if self.label is not None:
            self.set_label_item(self.label.plane_origin(self.view, self.position))

    # 切换图像
    def set_image(self, image: Union[MedicalImage, MedicalImage2]):
        self.image = image
        # 位置信息
        self._position = {
            "s": self.image.size[0] // 2 + 1,
            "c": self.image.size[1] // 2 + 1,
            "t": self.image.size[2] // 2 + 1,
        }
        self._position_max = {
            "s": self.image.size[0],
            "c": self.image.size[1],
            "t": self.image.size[2],
        }
        # 设置背景色
        if self.image.cmap is not None:
            self._scene.setBackgroundBrush(QColor(*[round(_ * 255) for _ in self.image.cmap(0)]))
        # 初始化缩放信息
        self.reset()
        # 添加图像
        self.set_image_item(self.image.plane(self.view, self.position))

    # 设置ImageItem
    def set_image_item(self, image_array: np.ndarray):
        if self.image_item is not None:
            self.scene().removeItem(self.image_item)  # 清除图像
        else:
            self.reset()  # 缩放

        self.image_item = ImageItem(image_array)
        self.scene().addItem(self.image_item)

    def set_label(self, label: MedicalImage):
        if self.image is None:
            warning("请先打开图像。")
        elif label.size != self.image.size:
            warning("分割图与图像的大小尺寸不同。")
        else:
            self.label = label
            self.set_label_item(self.label.plane_origin(self.view, self.position))

    def set_label_item(self, labelArray: np.ndarray):
        if self.label_item is not None:
            self.scene().removeItem(self.label_item)  # 清除分割图
        self.label_item = ImageItem2(labelArray, self.label_opacity)
        self.scene().addItem(self.label_item)

    def set_label_opacity(self, v: float):
        self.label_opacity = v
        if self.label_item is not None:
            self.label_item.setOpacity(self.label_opacity)

    # 设置当前平面
    def set_current_plane(self):
        if self.image is not None:
            self.set_image_item(self.image.plane(self.view, self.position))
        if self.label is not None:
            self.set_label_item(self.label.plane_origin(self.view, self.position))

    def mirror1(self):  # 水平镜像
        self.scale(-1, 1)

    def mirror2(self):  # 垂直镜像
        self.scale(1, -1)

    def rotate1(self):  # 顺时针90°
        self.rotate(90)

    def rotate2(self):  # 逆时针90°
        self.rotate(-90)
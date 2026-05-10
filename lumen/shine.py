"""Static "shine" / glow effect for hero buttons.

This matches the look in the FileHub reference image: each hero button
is a glossy pill with a soft outer halo. The halo intensifies on hover
and tightens on press. There is **no** sweeping animation — the surface
itself is what reads as polished.

Implementation:
    * QSS supplies the multi-stop vertical gradient (handled in theme.py).
    * ``ShineButton`` adds a ``QGraphicsDropShadowEffect`` whose blur
      radius and offset gently animate on enter/leave/press, creating
      the "lit from within" feel of the reference.
"""

from __future__ import annotations

from PyQt6.QtCore import (
    QEasingCurve,
    QEvent,
    QPropertyAnimation,
    pyqtProperty,
)
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect, QPushButton, QWidget


class ShineButton(QPushButton):
    """A QPushButton with a static, hover-reactive soft glow halo."""

    IDLE_BLUR = 18.0
    HOVER_BLUR = 36.0
    PRESS_BLUR = 8.0
    IDLE_ALPHA = 70
    HOVER_ALPHA = 150
    PRESS_ALPHA = 200

    def __init__(self, *args, intense: bool = False, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._intense = intense
        self._effect = QGraphicsDropShadowEffect(self)
        self._effect.setOffset(0, 2)
        self._effect.setColor(self._halo_color(self.IDLE_ALPHA))
        self._effect.setBlurRadius(
            self.IDLE_BLUR * (1.4 if intense else 1.0)
        )
        self.setGraphicsEffect(self._effect)

        self._blur_anim = QPropertyAnimation(self, b"halo_blur", self)
        self._blur_anim.setDuration(180)
        self._blur_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._alpha_anim = QPropertyAnimation(self, b"halo_alpha", self)
        self._alpha_anim.setDuration(180)
        self._alpha_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    # ---- Halo colour helper ----

    def _halo_color(self, alpha: int) -> QColor:
        # Soft white halo reads as "shine" on the dark UI; the same
        # halo on a light theme just reads as a polite focus glow.
        c = QColor(255, 255, 255)
        c.setAlpha(alpha)
        return c

    # ---- Animatable Q_PROPERTIES (blur + alpha) ----

    def _get_blur(self) -> float:
        return self._effect.blurRadius()

    def _set_blur(self, value: float) -> None:
        self._effect.setBlurRadius(float(value))

    halo_blur = pyqtProperty(float, fget=_get_blur, fset=_set_blur)

    def _get_alpha(self) -> int:
        return self._effect.color().alpha()

    def _set_alpha(self, value: int) -> None:
        self._effect.setColor(self._halo_color(int(value)))

    halo_alpha = pyqtProperty(int, fget=_get_alpha, fset=_set_alpha)

    # ---- Hover + press handling ----

    def _animate_to(self, blur: float, alpha: int) -> None:
        if self._intense:
            blur *= 1.25
        self._blur_anim.stop()
        self._blur_anim.setStartValue(self._effect.blurRadius())
        self._blur_anim.setEndValue(blur)
        self._blur_anim.start()

        self._alpha_anim.stop()
        self._alpha_anim.setStartValue(self._effect.color().alpha())
        self._alpha_anim.setEndValue(alpha)
        self._alpha_anim.start()

    def enterEvent(self, e: QEvent) -> None:  # noqa: N802
        super().enterEvent(e)
        if self.isEnabled():
            self._animate_to(self.HOVER_BLUR, self.HOVER_ALPHA)

    def leaveEvent(self, e: QEvent) -> None:  # noqa: N802
        super().leaveEvent(e)
        self._animate_to(self.IDLE_BLUR, self.IDLE_ALPHA)

    def mousePressEvent(self, e) -> None:  # noqa: N802
        super().mousePressEvent(e)
        self._animate_to(self.PRESS_BLUR, self.PRESS_ALPHA)

    def mouseReleaseEvent(self, e) -> None:  # noqa: N802
        super().mouseReleaseEvent(e)
        if self.underMouse() and self.isEnabled():
            self._animate_to(self.HOVER_BLUR, self.HOVER_ALPHA)
        else:
            self._animate_to(self.IDLE_BLUR, self.IDLE_ALPHA)


def attach_shine(widget: QWidget, *, intense: bool = False) -> ShineButton | None:
    """Return *widget* as a ShineButton if it isn't one already.

    A widget's class can't be swapped at runtime; construct
    ``ShineButton`` directly when you need shine.
    """
    return widget if isinstance(widget, ShineButton) else None


__all__ = ["ShineButton", "attach_shine"]

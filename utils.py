"""
图像预处理工具
"""
import cv2
import numpy as np
from PIL import Image
from typing import Tuple


def pil_to_cv2(img: Image.Image) -> np.ndarray:
    """PIL.Image → OpenCV BGR 格式"""
    return cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)


def cv2_to_pil(img: np.ndarray) -> Image.Image:
    """OpenCV BGR → PIL.Image"""
    return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))


def auto_rotate(image: np.ndarray) -> np.ndarray:
    """
    基于霍夫变换检测文字方向角，自动旋转校正。
    适合拍照上传时歪斜的文档图片。
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100,
                            minLineLength=50, maxLineGap=10)
    if lines is None or len(lines) == 0:
        return image

    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        if -90 <= angle <= 90:
            angles.append(angle)

    if not angles:
        return image

    median_angle = np.median(angles)
    if abs(median_angle) < 0.5:
        return image

    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h),
                              flags=cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_REPLICATE)
    return rotated


def increase_contrast(image: np.ndarray, clip_limit: float = 2.0,
                      tile_size: Tuple[int, int] = (8, 8)) -> np.ndarray:
    """CLAHE 对比度增强，适合光照不均的拍照文档"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_size)
    enhanced = clahe.apply(gray)
    return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)


def denoise(image: np.ndarray) -> np.ndarray:
    """中值滤波去噪"""
    return cv2.medianBlur(image, 3)


def sharpen(image: np.ndarray) -> np.ndarray:
    """锐化，突出文字边缘"""
    kernel = np.array([[-1, -1, -1],
                      [-1,  9, -1],
                      [-1, -1, -1]])
    return cv2.filter2D(image, -1, kernel)


def resize_by_width(image: np.ndarray, target_width: int = 1200) -> np.ndarray:
    """按宽度等比缩放，过大图片缩小加速OCR"""
    h, w = image.shape[:2]
    if w <= target_width:
        return image
    ratio = target_width / w
    return cv2.resize(image, (target_width, int(h * ratio)),
                     interpolation=cv2.INTER_AREA)


def preprocess_document(image: np.ndarray) -> np.ndarray:
    """
    完整预处理流水线：缩放 → 旋转校正 → 去噪 → 对比度增强 → 锐化
    """
    img = resize_by_width(image, 1400)
    img = auto_rotate(img)
    img = denoise(img)
    img = increase_contrast(img)
    img = sharpen(img)
    return img
import time
from pathlib import Path
from typing import Union, BinaryIO, List, Tuple, Literal
from math import sin, cos, radians, fabs

import cv2
import numpy as np


def load_image(image_data):
    """
    加载图像

    参数:
        image_data: 可以是文件路径(字符串或Path对象)、二进制数据(bytes)、文件类对象或已经是cv2图像(numpy数组)

    返回:
        处理后的图像
    """
    # 如果已经是numpy数组(OpenCV图像)，直接返回
    if isinstance(image_data, np.ndarray):
        return image_data

    # 处理路径输入
    if isinstance(image_data, (str, Path)):
        img = cv2.imread(str(image_data))
    # 处理二进制数据
    elif isinstance(image_data, bytes):
        img = cv2.imdecode(np.frombuffer(image_data, np.uint8), cv2.IMREAD_COLOR)
    # 处理文件类对象(如上传的文件)
    elif hasattr(image_data, 'read'):
        img = cv2.imdecode(np.frombuffer(image_data.read(), np.uint8), cv2.IMREAD_COLOR)
    else:
        raise ValueError("不支持的输入类型，请提供文件路径、二进制数据、文件类对象或cv2图像(numpy数组)")

    return img


def load_and_preprocess(image_data: Union[str, Path, bytes, BinaryIO, np.ndarray], threshold: int = 30) -> np.ndarray:
    """
    加载图像并预处理，提取接近黑色的部分（基于BGR色彩空间）

    参数:
        image_data: 可以是文件路径(字符串或Path对象)、二进制数据(bytes)或文件类对象
        threshold: 黑色阈值，所有BGR通道都低于此值被视为黑色

    返回:
        处理后的二值化掩码图像
    """
    img = load_image(image_data)

    if img is None:
        raise ValueError("图像加载失败，请检查输入数据是否正确")

    # 创建一个掩码，其中所有BGR通道都低于阈值
    return cv2.inRange(img, (0, 0, 0), (threshold, threshold, threshold))


def should_merge(rect1: Tuple[int, int, int, int], rect2: Tuple[int, int, int, int],
                 overlap_threshold: float = 0.0) -> bool:
    """判断两个矩形是否应该合并

    Args:
        rect1: 第一个矩形 (x, y, width, height)
        rect2: 第二个矩形 (x, y, width, height)
        overlap_threshold: 重叠面积占较小矩形面积的比例阈值

    Returns:
        bool: 如果应该合并返回True，否则返回False
    """
    x1, y1, w1, h1 = rect1
    x2, y2, w2, h2 = rect2

    # 计算两个矩形的交集区域
    x_left = max(x1, x2)
    y_top = max(y1, y2)
    x_right = min(x1 + w1, x2 + w2)
    y_bottom = min(y1 + h1, y2 + h2)

    if x_right <= x_left or y_bottom <= y_top:
        return False  # 没有交集

    # 如果阈值为0，只要有重叠就合并
    if overlap_threshold == 0:
        return True

    # 计算交集面积
    intersection_area = (x_right - x_left) * (y_bottom - y_top)

    # 计算两个矩形中较小矩形的面积
    area1 = w1 * h1
    area2 = w2 * h2
    min_area = min(area1, area2)

    # 如果交集面积超过较小矩形面积的阈值比例，则合并
    return intersection_area > overlap_threshold * min_area


def merge_rectangles(rectangles: List[Tuple[int, int, int, int]],
                     overlap_threshold: float = 0.0) -> List[Tuple[int, int, int, int]]:
    """合并重叠的矩形

    Args:
        rectangles: 矩形列表，每个矩形表示为(x, y, width, height)
        overlap_threshold: 重叠面积占较小矩形面积的比例阈值，0表示只要有重叠就合并

    Returns:
        合并后的矩形列表
    """
    if not rectangles:
        return []

    # 创建一个副本以避免修改原始列表
    rects = [rect for rect in rectangles]
    changed = True

    # 持续合并直到没有更多合并发生
    while changed:
        changed = False
        new_rects = []
        merged_indices = set()

        for i in range(len(rects)):
            if i in merged_indices:
                continue

            current = rects[i]
            merged_rect = current

            # 尝试与后面的所有矩形合并
            for j in range(i + 1, len(rects)):
                if j in merged_indices:
                    continue

                candidate = rects[j]
                if should_merge(merged_rect, candidate, overlap_threshold):
                    # 计算合并后的矩形边界
                    x_min = min(merged_rect[0], candidate[0])
                    y_min = min(merged_rect[1], candidate[1])
                    x_max = max(merged_rect[0] + merged_rect[2], candidate[0] + candidate[2])
                    y_max = max(merged_rect[1] + merged_rect[3], candidate[1] + candidate[3])
                    merged_rect = (x_min, y_min, x_max - x_min, y_max - y_min)
                    merged_indices.add(j)
                    changed = True

            new_rects.append(merged_rect)

        rects = new_rects

    return rects


def merge_close_rectangles(rectangles, max_distance):
    """
    合并边缘距离相近的矩形

    参数:
        rectangles: 矩形列表，每个矩形表示为(x, y, w, h)
        max_distance: 最大合并距离

    返回:
        合并后的矩形列表
    """

    # 我们需要一个辅助函数来计算两个矩形之间的最小距离
    def rect_distance(r1, r2):
        # 矩形1的坐标
        x1, y1, w1, h1 = r1
        x1_end, y1_end = x1 + w1, y1 + h1

        # 矩形2的坐标
        x2, y2, w2, h2 = r2
        x2_end, y2_end = x2 + w2, y2 + h2

        # 计算水平距离
        if x1_end < x2:
            dx = x2 - x1_end
        elif x2_end < x1:
            dx = x1 - x2_end
        else:
            dx = 0

        # 计算垂直距离
        if y1_end < y2:
            dy = y2 - y1_end
        elif y2_end < y1:
            dy = y1 - y2_end
        else:
            dy = 0

        # 返回欧几里得距离
        return (dx ** 2 + dy ** 2) ** 0.5

    changed = True
    while changed and len(rectangles) > 1:
        changed = False
        new_rectangles = []
        merged = [False] * len(rectangles)

        for i in range(len(rectangles)):
            if merged[i]:
                continue

            rect1 = rectangles[i]
            current_rect = rect1

            for j in range(i + 1, len(rectangles)):
                if merged[j]:
                    continue

                rect2 = rectangles[j]
                distance = rect_distance(current_rect, rect2)

                if distance <= max_distance:
                    # 合并两个矩形
                    x = min(current_rect[0], rect2[0])
                    y = min(current_rect[1], rect2[1])
                    w = max(current_rect[0] + current_rect[2], rect2[0] + rect2[2]) - x
                    h = max(current_rect[1] + current_rect[3], rect2[1] + rect2[3]) - y
                    current_rect = (x, y, w, h)
                    merged[j] = True
                    changed = True

            new_rectangles.append(current_rect)
            merged[i] = True

        rectangles = new_rectangles

    return rectangles


def extract_black_regions(
        binary_image,
        min_area: int = 100,
        merged: bool = True,
        merge_distance: int = 0,
        sort_mode: Literal["area-desc", "area-asc", "position-tl", "position-l"] = "area-desc"
) -> List[Tuple[int, int, int, int]]:
    """
    提取二值图像中的黑色区域(矩形)

    参数:
        binary_image: 二值图像
        min_area: 最小区域面积阈值
        merged: 是否合并重叠矩形
        merge_distance: 合并距离阈值，如果两个矩形边缘距离小于此值则合并
        sort_mode: 排序模式
            "area-desc": 按面积从大到小
            "area-asc": 按面积从小到大
            "position-tl": 按位置从上到下、从左到右
            "position-l": 按位置从左到右

    返回:
        矩形列表，每个矩形表示为(x, y, w, h)
    """
    # 寻找轮廓 - 现在寻找白色区域（即原始图像中的黑色区域）
    contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 获取每个轮廓的边界矩形并过滤掉太小的区域
    rectangles = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w * h >= min_area:  # 忽略面积太小的区域
            rectangles.append((x, y, w, h))

    if merged:
        # 合并重叠的矩形
        rectangles = merge_rectangles(rectangles)

    # 如果设置了合并距离，合并边缘距离相近的矩形
    if merge_distance > 0 and len(rectangles) > 1:
        # 计算矩形间的距离并合并
        rectangles = merge_close_rectangles(rectangles, merge_distance)

    # 根据排序模式进行排序
    if sort_mode == "area-desc":
        rectangles.sort(key=lambda rect: rect[2] * rect[3], reverse=True)
    elif sort_mode == "area-asc":
        rectangles.sort(key=lambda rect: rect[2] * rect[3])
    elif sort_mode == "position-tl":
        # 先按y坐标排序（从上到下），然后按x坐标排序（从左到右）
        rectangles.sort(key=lambda rect: (rect[1], rect[0]))
    elif sort_mode == "position-l":
        # 按x坐标排序（从左到右）
        rectangles.sort(key=lambda rect: rect[0])

    return rectangles


def display_black_regions(original_image, rectangles):
    """在原始图像上显示提取的黑色区域矩形"""
    # 创建原始图像的副本用于绘制
    img_with_rectangles = original_image.copy()

    # 绘制所有矩形
    for i, (x, y, w, h) in enumerate(rectangles):
        # 绘制矩形
        cv2.rectangle(img_with_rectangles, (x, y), (x + w, y + h), (0, 255, 0), 2)
        # 添加序号
        cv2.putText(img_with_rectangles, str(i + 1), (x, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("警告: 未安装 matplotlib，跳过可视化（调试功能）。可执行 pip install matplotlib 启用。")
        return

    # 显示结果
    plt.figure(figsize=(10, 6))
    plt.imshow(cv2.cvtColor(img_with_rectangles, cv2.COLOR_BGR2RGB))
    plt.title('Detected Black Regions (Merged Rectangles)')
    plt.axis('off')
    plt.show()


def opencv_rotate(image, angle, scale=1.0):
    """
    https://cloud.tencent.com/developer/article/1798209
    使用OpenCV旋转图像，并调整画布大小以适应旋转后的图像

    参数:
        image: 输入图像 (numpy数组)
        angle: 旋转角度 (顺时针为正方向，单位：度)
        scale: 缩放比例

    返回:
        rotated_image: 旋转后的图像
    """
    # 获取图像高度和宽度
    height, width = image.shape[:2]

    # 计算图像中心点
    center = (width / 2, height / 2)

    # 获取旋转矩阵
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, scale)

    # 计算旋转后新图像的尺寸
    new_height = int(width * fabs(sin(radians(angle))) + height * fabs(cos(radians(angle))))
    new_width = int(height * fabs(sin(radians(angle))) + width * fabs(cos(radians(angle))))

    # 调整旋转矩阵的平移部分，使图像居中
    rotation_matrix[0, 2] += (new_width - width) / 2
    rotation_matrix[1, 2] += (new_height - height) / 2

    # 执行仿射变换，使用黑色填充边界
    rotated_image = cv2.warpAffine(
        image,
        rotation_matrix,
        (new_width, new_height),
        borderValue=(0, 0, 0)
    )

    return rotated_image


def analyze_rotated_regions(sprite_mask, sprite_black_regions):
    """分析每个sprite黑色区域在不同旋转角度下的轮廓"""
    rotation_data = []

    for region_idx, (x, y, w, h) in enumerate(sprite_black_regions):
        # 提取当前区域的ROI
        region_roi = sprite_mask[y:y + h, x:x + w]

        # 存储当前区域的所有旋转信息
        region_data = {
            'original_region': (x, y, w, h),
            'rotations': []
        }

        # 从-45度到45度，步长1度
        for angle in range(-45, 46):
            # 旋转图像
            rotated_img = opencv_rotate(region_roi, -angle)

            # 获取轮廓的边界矩形
            rects = extract_black_regions(rotated_img, 0)

            # 合并所有矩形
            if rects:
                x_r, y_r, w_r, h_r = rects[0]  # 取第一个也是唯一一个矩形
                aspect_ratio = round(float(w_r) / h_r, 12) if h_r != 0 else float('inf')

                # 存储旋转信息
                rotation_info = {
                    'angle': angle,
                    'rect': (x_r, y_r, w_r, h_r),
                    'aspect_ratio': aspect_ratio,
                    'rotated_image': rotated_img
                }
                region_data['rotations'].append(rotation_info)

        rotation_data.append(region_data)

    return rotation_data


def display_rotation_analysis(rotation_data, original_sprite):
    """展示每个sprite区域的旋转分析结果"""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("警告: 未安装 matplotlib，跳过可视化（调试功能）。可执行 pip install matplotlib 启用。")
        return

    for idx, region_data in enumerate(rotation_data):
        plt.figure(figsize=(16, 8))

        # 显示原始图像中的区域
        x, y, w, h = region_data['original_region']
        original_roi = original_sprite[y:y + h, x:x + w]

        plt.subplot(2, 1, 1)
        plt.imshow(cv2.cvtColor(original_roi, cv2.COLOR_BGR2RGB))
        plt.title(f'Sprite Region {idx + 1} (Original)')
        plt.axis('off')

        # 显示所有旋转结果
        plt.subplot(2, 1, 2)

        # 计算最大宽度和高度，确定网格单元大小
        max_width = max(rot['rect'][2] for rot in region_data['rotations'])
        max_height = max(rot['rect'][3] for rot in region_data['rotations'])
        cell_size = max(max_width, max_height) + 20  # 加上边距

        # 创建网格参数
        num_angles = len(region_data['rotations'])
        cols = 10  # 每行显示10个角度
        rows = (num_angles + cols - 1) // cols

        # 创建网格图像
        grid = np.zeros((rows * cell_size, cols * cell_size), dtype=np.uint8) + 200  # 灰色背景

        for i, rot in enumerate(region_data['rotations']):
            row = i // cols
            col = i % cols

            # 获取旋转后的图像和其矩形信息
            rotated_img = rot['rotated_image']
            x_r, y_r, w_r, h_r = rot['rect']
            roi = rotated_img[y_r:y_r + h_r, x_r:x_r + w_r]

            # 计算在网格中的位置(居中放置)
            y_start = row * cell_size + (cell_size - h_r) // 2
            x_start = col * cell_size + (cell_size - w_r) // 2

            # 将图像放入网格
            grid[y_start:y_start + h_r, x_start:x_start + w_r] = roi

            # 添加角度标签(放在图像下方)
            label_y = row * cell_size + cell_size - 5
            label_x = col * cell_size + 5
            cv2.putText(grid, f"{rot['angle']} deg", (label_x, label_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, 0, 1)  # 黑色文字

        plt.imshow(grid, cmap='gray', vmin=0, vmax=255)
        plt.title(f'Rotation Analysis (-45° to 45°) - Preserved Aspect Ratio')
        plt.axis('off')

        plt.tight_layout()
        plt.show()

        # 打印旋转信息
        print(f"\nRegion {idx + 1} Rotation Analysis:")
        print("Angle | Width | Height | Aspect Ratio")
        for rot in region_data['rotations']:
            x_r, y_r, w_r, h_r = rot['rect']
            print(f"{rot['angle']:5}° | {w_r:5} | {h_r:6} | {rot['aspect_ratio']:.12f}")


def binary_similarity(img1, img2):
    # 使用向量化比较
    matching_pixels = np.count_nonzero((img1 > 127) == (img2 > 127))
    return (matching_pixels / img1.size) * 100


def brute_search(rotated_roi, bg_roi, bg_rect, w_r, h_r):
    max_similarity = -1
    best_bg_sub_rect = None
    bg_x, bg_y, bg_w, bg_h = bg_rect

    # 计算滑动窗口的范围
    for y in range(0, bg_h - h_r + 1):
        for x in range(0, bg_w - w_r + 1):
            # 获取当前窗口的ROI
            bg_sub_roi = bg_roi[y:y + h_r, x:x + w_r]

            # 计算相似度
            current_sim = binary_similarity(rotated_roi, bg_sub_roi)

            # 更新最大相似度和最佳位置
            if current_sim > max_similarity:
                max_similarity = current_sim
                best_bg_sub_rect = (bg_x + x, bg_y + y, w_r, h_r)
    return best_bg_sub_rect, max_similarity


def template_search(rotated_roi, bg_roi, bg_rect, w_r, h_r):
    bg_x, bg_y, bg_w, bg_h = bg_rect

    # 确保输入是二值图像（0和255），并转换为单通道
    template = rotated_roi.astype(np.uint8)
    search_area = bg_roi[:bg_h, :bg_w].astype(np.uint8)

    # 使用 cv2.matchTemplate（TM_CCORR_NORMED 或 TM_CCOEFF_NORMED）
    res = cv2.matchTemplate(search_area, template, cv2.TM_CCOEFF_NORMED)

    # 找到最佳匹配位置
    _, max_val, _, max_pos = cv2.minMaxLoc(res)
    max_similarity = max_val * 100  # 转换为百分比

    # 返回匹配位置
    best_bg_sub_rect = (bg_x + max_pos[0], bg_y + max_pos[1], w_r, h_r)
    return best_bg_sub_rect, max_similarity


def match_sprite_to_background(bg_black_regions, preprocessed_bg, rotation_data, method='template'):
    """
    将sprite区域与背景黑色区域进行匹配

    参数:
        bg_black_regions: 背景中的黑色区域列表
        preprocessed_bg: 预处理后的二值化背景图像
        rotation_data: sprite旋转分析数据
        method: 匹配背景块方法

    返回:
        匹配结果列表，每个元素是一个字典包含匹配信息
    """
    func = {
        'template': template_search,
        'brute': brute_search
    }.get(method, None)

    # 存储所有可能的匹配（包括冲突的）
    all_matches = []

    # 第一阶段：收集所有可能的匹配
    for sprite_idx, sprite_data in enumerate(rotation_data):
        # 遍历每个背景区域
        for bg_idx, bg_rect in enumerate(bg_black_regions):
            # 比较这些角度
            for rotation in sprite_data['rotations']:
                # 获取旋转后的图像
                rotated_img = rotation['rotated_image']
                x_r, y_r, w_r, h_r = rotation['rect']

                # 裁剪出旋转后的有效区域
                rotated_roi = rotated_img[y_r:y_r + h_r, x_r:x_r + w_r]

                # 准备背景ROI
                bg_x, bg_y, bg_w, bg_h = bg_rect
                bg_roi = preprocessed_bg[bg_y:bg_y + bg_h, bg_x:bg_x + bg_w]

                if func is None:
                    # 速度匹配
                    # 调整大小使两个ROI相同尺寸
                    max_width = max(w_r, bg_w)
                    max_height = max(h_r, bg_h)

                    # 调整sprite ROI
                    sprite_resized = cv2.resize(rotated_roi, (max_width, max_height),
                                                interpolation=cv2.INTER_NEAREST)

                    # 调整背景ROI
                    bg_resized = cv2.resize(bg_roi, (max_width, max_height),
                                            interpolation=cv2.INTER_NEAREST)

                    # 计算相似度
                    similarity = binary_similarity(sprite_resized, bg_resized)

                    best_bg_sub_rect = bg_rect
                else:
                    # 检查是否需要调整rotated_roi的大小
                    if h_r > bg_h or w_r > bg_w:
                        # 计算新的尺寸，只缩小较大的维度
                        new_w = min(w_r, bg_w)  # 如果w_r > bg_w则缩小宽度，否则保持
                        new_h = min(h_r, bg_h)  # 如果h_r > bg_h则缩小高度，否则保持

                        # 缩放rotated_roi
                        rotated_roi = cv2.resize(rotated_roi, (new_w, new_h), interpolation=cv2.INTER_NEAREST)
                        w_r, h_r = new_w, new_h

                    # 在bg_roi上滑动窗口进行比较
                    best_bg_sub_rect, similarity = func(rotated_roi, bg_roi, bg_rect, w_r, h_r)

                # 存储最佳匹配
                all_matches.append({
                    'sprite_idx': sprite_idx,
                    'bg_idx': bg_idx,
                    'angle': rotation['angle'],
                    'similarity': similarity,
                    'sprite_rect': sprite_data['original_region'],
                    'bg_rect': best_bg_sub_rect,
                    'rotated_sprite': rotated_roi
                })

    # 第二阶段：解决冲突，选择最佳匹配
    final_matches = []
    used_bg_regions = set()
    used_sprites = set()

    # 按相似度降序排序所有匹配
    all_matches.sort(key=lambda x_: -x_['similarity'])

    # 遍历排序后的匹配，选择最佳且不冲突的
    for match in all_matches:
        sprite_idx = match['sprite_idx']
        bg_idx = match['bg_idx']

        # 如果sprite已被使用，跳过
        if sprite_idx in used_sprites:
            continue

        # 如果不使用滑动窗口匹配，跳过同一个背景区域
        if func is None and bg_idx in used_bg_regions:
            continue

        # 添加到最终匹配结果
        final_matches.append(match)
        used_sprites.add(sprite_idx)
        used_bg_regions.add(bg_idx)

        # 如果所有sprite或背景区域都已匹配，提前退出
        if len(used_sprites) == len(rotation_data):
            break

        if func is None and len(used_bg_regions) == len(bg_black_regions):
            break

    # 按照 sprite_idx 从小到大排序
    final_matches = sorted(final_matches, key=lambda x: x.get('sprite_idx', 'inf'))

    return final_matches


def display_matches_on_background(original_bg, matches):
    """
    在原始背景图像上显示所有匹配结果

    参数:
        original_bg: 原始背景图像
        matches: 匹配结果列表
    """
    # 创建背景图像的副本用于绘制
    bg_with_matches = original_bg.copy()

    # 为每个匹配绘制信息
    for match in matches:
        # 绘制背景区域矩形
        bg_x, bg_y, bg_w, bg_h = match['bg_rect']
        cv2.rectangle(bg_with_matches, (bg_x, bg_y),
                      (bg_x + bg_w, bg_y + bg_h), (0, 255, 0), 2)

        # 添加文本信息
        text = f"Sprite {match['sprite_idx'] + 1} (Angle: {match['angle']} deg, Sim: {match['similarity']:.1f}%)"
        cv2.putText(bg_with_matches, text, (bg_x, bg_y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("警告: 未安装 matplotlib，跳过可视化（调试功能）。可执行 pip install matplotlib 启用。")
        return

    # 显示结果
    plt.figure(figsize=(12, 8))
    plt.imshow(cv2.cvtColor(bg_with_matches, cv2.COLOR_BGR2RGB))
    plt.title('Matched Sprite Regions on Background')
    plt.axis('off')
    plt.show()


def display_match_comparisons(original_bg, original_sprite, matches):
    """
    显示每个sprite及其匹配的背景区域的详细比较

    参数:
        original_bg: 原始背景图像
        original_sprite: 原始sprite图像
        matches: 匹配结果列表
    """
    num_matches = len(matches)

    # 如果没有匹配，直接返回
    if num_matches == 0:
        print("No matches found")
        return

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("警告: 未安装 matplotlib，跳过可视化（调试功能）。可执行 pip install matplotlib 启用。")
        return

    # 创建一个大图，每个match一行，每行3列
    fig, axes = plt.subplots(num_matches, 3, figsize=(12, 4 * num_matches))

    # 如果只有一个匹配，axes的维度会不同，需要调整
    if num_matches == 1:
        axes = axes.reshape(1, -1)

    for i, match in enumerate(matches):
        # 显示sprite区域
        sprite_x, sprite_y, sprite_w, sprite_h = match['sprite_rect']
        sprite_roi = original_sprite[sprite_y:sprite_y + sprite_h, sprite_x:sprite_x + sprite_w]
        axes[i, 0].imshow(cv2.cvtColor(sprite_roi, cv2.COLOR_BGR2RGB))
        axes[i, 0].set_title(f'Sprite {match["sprite_idx"] + 1} (Original)')
        axes[i, 0].axis('off')

        # 显示旋转后的sprite
        rotated_sprite = cv2.cvtColor(match['rotated_sprite'], cv2.COLOR_GRAY2BGR)
        axes[i, 1].imshow(rotated_sprite)
        axes[i, 1].set_title(f'Rotated {match["angle"]}°')
        axes[i, 1].axis('off')

        # 显示匹配的背景区域
        bg_x, bg_y, bg_w, bg_h = match['bg_rect']
        bg_roi = original_bg[bg_y:bg_y + bg_h, bg_x:bg_x + bg_w]
        axes[i, 2].imshow(cv2.cvtColor(bg_roi, cv2.COLOR_BGR2RGB))
        axes[i, 2].set_title(f'Matched BG Region\nSimilarity: {match["similarity"]:.1f}%')
        axes[i, 2].axis('off')

    plt.tight_layout()
    plt.show()


def preprocess_mask(img, scale_factor: Union[int, float] = 4, kernel_size=2, iterations=1):
    # 创建膨胀核
    kernel = np.ones((kernel_size, kernel_size), np.uint8)

    # 图像膨胀
    img = cv2.dilate(img, kernel, iterations=iterations)

    # 减分辨率(使用区域平均)
    height, width = img.shape
    img = cv2.resize(img,
                     (int(width // scale_factor), int(height // scale_factor)),
                     interpolation=cv2.INTER_AREA)

    # 再次二值化(因为降采样可能导致灰度变化)
    _, img = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)

    # 使用最近邻插值进行放大
    img = cv2.resize(img,
                     (width, height),
                     interpolation=cv2.INTER_NEAREST)

    return img


def main(bg_data, sprite_data, match_method='template', show_results=False, show_preprocessed=False):
    # 加载原始背景图像
    original_bg = load_image(bg_data)

    # 加载Sprite图像
    original_sprite = load_image(sprite_data)

    height, width = original_sprite.shape[:2]
    original_sprite = cv2.resize(
        original_sprite,
        (int(width * 1.55), int(height * 1.55)),
        interpolation=cv2.INTER_NEAREST
    )

    # 预处理图像
    bg_mask = load_and_preprocess(original_bg, 25)
    sprite_mask = load_and_preprocess(original_sprite)

    bg_mask = preprocess_mask(bg_mask)
    sprite_mask = preprocess_mask(sprite_mask, 1)

    # 如果需要显示预处理结果
    if show_preprocessed:
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print("警告: 未安装 matplotlib，跳过预处理结果可视化（调试功能）。可执行 pip install matplotlib 启用。")
        else:
            plt.figure(figsize=(12, 6))

            plt.subplot(1, 2, 1)
            plt.imshow(bg_mask, cmap='gray')
            plt.title('Preprocessed Background')

            plt.subplot(1, 2, 2)
            plt.imshow(sprite_mask, cmap='gray')
            plt.title('Preprocessed Sprite')

            plt.tight_layout()
            plt.show()

    # 提取背景图像中的黑色区域并合并重叠的（选取最大的10个）
    bg_black_regions = extract_black_regions(bg_mask, 50, merge_distance=5)[:10]
    # 提取Sprite图像中的黑色区域
    sprite_black_regions = extract_black_regions(sprite_mask, sort_mode="position-l")

    # 分析旋转后的sprite区域
    rotation_data = analyze_rotated_regions(sprite_mask, sprite_black_regions)

    if show_preprocessed:
        display_black_regions(original_bg, bg_black_regions)
        display_black_regions(original_sprite, sprite_black_regions)

        display_rotation_analysis(rotation_data, original_sprite)

    # 匹配sprite到背景区域
    matches = match_sprite_to_background(bg_black_regions, bg_mask, rotation_data, match_method)

    # 显示匹配结果
    if show_results:
        display_matches_on_background(original_bg, matches)
        display_match_comparisons(original_bg, original_sprite, matches)

    for match in matches:
        if 'sprite_rect' in match:
            original_tuple = match['sprite_rect']
            scaled_tuple = tuple(int(x // 1.55) for x in original_tuple)
            match['sprite_rect'] = scaled_tuple

    return matches


def convert_matches_to_positions(matches):
    positions = []
    for data in matches:
        x, y, w, h = data['bg_rect']
        positions.append((x + w / 2, y + h / 2))
    return positions


def find_part_positions(bg_img, sprite_img, match_method='template'):
    """在图像中查找所有sprite部分的位置，返回中心点坐标列表"""
    return convert_matches_to_positions(
        main(bg_img, sprite_img, match_method, False, False)
    )


if __name__ == "__main__":
    # 使用示例图片路径
    bg = "temp/captcha.jpg"
    sprite = "temp/sprite.jpg"

    # 检查文件是否存在
    if not Path(bg).exists() or not Path(sprite).exists():
        print("测试图片不存在，请确保tests/bg.jpg和tests/sprite.jpg存在")
    else:
        start_time = time.time()
        result = main(bg, sprite, 'template', True, True)
        # result = main(bg, sprite, 'template', False, False)
        end_time = time.time()
        execution_time = end_time - start_time
        for info in result:
            print(f"Sprite {info['sprite_idx']} -> {info['bg_rect']}")
        print(f"识别耗时: {execution_time:.4f} 秒")

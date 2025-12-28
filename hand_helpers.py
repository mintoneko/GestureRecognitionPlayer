import numpy as np

def get_angle(v1, v2):
    """计算两个向量之间的角度"""
    # 注意：原始代码中的 3.14 是 pi 的近似值，使用 np.pi 更精确。
    # angle = np.arccos(angle) / 3.14 * 180
    angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    angle = np.arccos(np.clip(angle, -1.0, 1.0))  # 使用 clip 增加数值稳定性
    return np.degrees(angle)


def get_finger_direction(finger_tip_idx, list_lms, min_vector_length_ratio=0.3):
    """
    根据单个伸出的手指，判断其指向。此版本更精确。
    通过引入角度阈值和向量长度阈值，避免对角线和微小移动的误判。

    :param finger_tip_idx: 伸出手指的指尖 landmark 索引 (4, 8, 12, 16, 20)
    :param list_lms: 所有手部关键点的坐标列表
    :param min_vector_length_ratio: 手指向量长度与手掌参考长度的最小比例，低于此值则忽略。
    :return: "Up", "Down", "Left", "Right" 或 None
    """
    # 1. 定义指尖到指根的映射关系
    tip_to_base_map = {
        4: 2, 8: 5, 12: 9, 16: 13, 20: 17
    }
    if finger_tip_idx not in tip_to_base_map:
        return None

    # 2. 计算方向向量 (从基点指向指尖)
    tip_point = np.array(list_lms[finger_tip_idx])
    base_point = np.array(list_lms[tip_to_base_map[finger_tip_idx]])
    direction_vector = tip_point - base_point

    # 3. 幅度阈值检查：确保手指是明确伸出的
    # 我们使用手腕(0)到中指根(9)的距离作为手掌大小的参考基准
    wrist_point = np.array(list_lms[0])
    mcp_point = np.array(list_lms[9])
    reference_length = np.linalg.norm(wrist_point - mcp_point)

    vector_length = np.linalg.norm(direction_vector)

    # 如果向量长度太短，则认为是没有明确指向的手势
    if vector_length < reference_length * min_vector_length_ratio:
        return None

    # 4. 角度阈值检查：计算向量角度并判断方向
    # 使用 atan2 计算向量与x轴正方向的角度。
    # 我们对y轴分量取反(-direction_vector[1])，因为在图像坐标系中y轴向下为正。
    # 这样可以将其转换为标准的数学坐标系（y轴向上为正）。
    angle_rad = np.arctan2(-direction_vector[1], direction_vector[0])
    angle_deg = np.degrees(angle_rad)

    # 定义每个方向的角度范围（每个方向覆盖90度）
    # 例如： "Right" 覆盖 (-45, 45] 度
    if -45 < angle_deg <= 45:
        return "Right"
    elif 45 < angle_deg <= 135:
        return "Up"
    elif angle_deg > 135 or angle_deg <= -135:
        return "Left"
    elif -135 < angle_deg <= -45:
        return "Down"
    else:
        # 理论上不会进入这个分支，但作为保险
        return None


# ===================== 修改后的核心函数 =====================
def get_str_guester(up_fingers, list_lms):
    """
    识别手势。此版本被修改为只响应“食指”的指向。

    :param up_fingers: 伸出的手指尖索引列表，例如 [8] 表示食指伸出。
    :param list_lms: 所有手部关键点的坐标列表。
    :return: 如果是食指指向，返回 "Up", "Down", "Left", "Right"；否则返回 " "。
    """
    # MediaPipe 中，食指指尖的索引是 8
    INDEX_FINGER_TIP = 8

    # 判断条件：
    # 1. 伸出的手指数量必须是 1 个。
    # 2. 这个伸出的手指必须是食指 (索引为 8)。
    if len(up_fingers) == 1 and up_fingers[0] == INDEX_FINGER_TIP:
        # 如果条件满足，才去判断食指的方向
        direction = get_finger_direction(INDEX_FINGER_TIP, list_lms)
        if direction:
            return direction

    # 对于所有其他情况 (例如没有手指伸出、伸出多个手指、或者伸出的不是食指)，
    # 都返回一个空字符串，表示不识别为任何有效指令。
    return " "

# =============================================================
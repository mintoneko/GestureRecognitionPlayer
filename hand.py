# --- FILE: hand.py ---

import numpy as np


def get_finger_direction(finger_tip_idx, list_lms, min_vector_length_ratio=0.2):
    """
    计算手指指向的方向
    :param finger_tip_idx: 指尖索引 (通常用 8 代表食指)
    :param list_lms: 关键点列表
    :return: "Up", "Down", "Left", "Right" or None
    """
    # 指尖到指根映射
    tip_to_base_map = {4: 2, 8: 5, 12: 9, 16: 13, 20: 17}
    if finger_tip_idx not in tip_to_base_map:
        return None

    # 向量计算 (只取 x, y)
    tip_point = np.array(list_lms[finger_tip_idx][:2])
    base_point = np.array(list_lms[tip_to_base_map[finger_tip_idx]][:2])
    direction_vector = tip_point - base_point

    # 长度校验 (归一化参照：手腕到中指根)
    wrist = np.array(list_lms[0][:2])
    mcp = np.array(list_lms[9][:2])
    ref_len = np.linalg.norm(wrist - mcp)

    if np.linalg.norm(direction_vector) < ref_len * min_vector_length_ratio:
        return None

    # 角度计算 (y轴向下为正，取反转为标准坐标系)
    angle_deg = np.degrees(np.arctan2(-direction_vector[1], direction_vector[0]))

    # 判断方向
    if -45 < angle_deg <= 45:
        return "Right"
    elif 45 < angle_deg <= 135:
        return "Up"
    elif angle_deg > 135 or angle_deg <= -135:
        return "Left"
    elif -135 < angle_deg <= -45:
        return "Down"
    return None


def get_gesture_state(up_fingers, list_lms):
    """
    核心手势判断逻辑
    :param up_fingers: 伸出的手指索引列表
    :param list_lms: 关键点坐标
    :return: (模式, 方向/动作)
             模式: "FIST", "PALM", "ONCE", "CONTINUE", "NONE"
             方向: "Up", "Down", "Left", "Right", "Play", "Pause", None
    """
    num_fingers = len(up_fingers)

    # 1. 握拳 (0指伸出) -> 暂停
    if num_fingers == 0:
        return "FIST", "Pause"

    # 2. 五指张开 (>=5指伸出) -> 播放
    if num_fingers >= 5:
        return "PALM", "Play"

    # 3. 单指 (食指 8) -> ONCE (单次触发)
    # 条件：只有1根手指，且必须是食指(8)
    if num_fingers == 1 and 8 in up_fingers:
        direction = get_finger_direction(8, list_lms)
        if direction:
            return "ONCE", direction

    # 4. 双指 (食指 8 + 中指 12) -> CONTINUE (连续触发)
    # 条件：2根手指，必须包含食指(8)和中指(12)
    if num_fingers == 2 and 8 in up_fingers and 12 in up_fingers:
        # 双指并拢时，用食指的方向代表整体方向即可
        direction = get_finger_direction(8, list_lms)
        if direction:
            return "CONTINUE", direction

    return "NONE", None
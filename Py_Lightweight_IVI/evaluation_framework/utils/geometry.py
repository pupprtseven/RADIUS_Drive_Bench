def check_collision(rect1, rect2):
    x1_min = min([p[0] for p in rect1])
    x1_max = max([p[0] for p in rect1])
    y1_min = min([p[1] for p in rect1])
    y1_max = max([p[1] for p in rect1])

    x2_min = min([p[0] for p in rect2])
    x2_max = max([p[0] for p in rect2])
    y2_min = min([p[1] for p in rect2])
    y2_max = max([p[1] for p in rect2])

    overlap_x = (x1_min <= x2_max) and (x1_max >= x2_min)
    overlap_y = (y1_min <= y2_max) and (y1_max >= y2_min)
    return overlap_x and overlap_y

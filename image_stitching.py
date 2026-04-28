import cv2 as cv
import numpy as np
import os

def stitch_pair(img_left, img_right):
    gray_left = cv.cvtColor(img_left, cv.COLOR_BGR2GRAY)
    _, mask_left = cv.threshold(gray_left, 1, 255, cv.THRESH_BINARY)

    sift = cv.SIFT_create()
    kp1, des1 = sift.detectAndCompute(img_left, mask_left)
    kp2, des2 = sift.detectAndCompute(img_right, None)

    bf = cv.BFMatcher()
    matches = bf.knnMatch(des2, des1, k=2)

    good_matches = []
    for match in matches:
        if len(match) == 2:
            m, n = match
            if m.distance < 0.75 * n.distance:
                good_matches.append(m)

    if len(good_matches) > 4:
        src_pts = np.float32([kp2[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp1[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        
        H, _ = cv.findHomography(src_pts, dst_pts, cv.RANSAC, 5.0)

        h1, w1 = img_left.shape[:2]
        h2, w2 = img_right.shape[:2]
        
        pts_right = np.float32([[0, 0], [0, h2], [w2, h2], [w2, 0]]).reshape(-1, 1, 2)
        dst_right = cv.perspectiveTransform(pts_right, H)
        pts_left = np.float32([[0, 0], [0, h1], [w1, h1], [w1, 0]]).reshape(-1, 1, 2)
        
        all_pts = np.concatenate((dst_right, pts_left), axis=0)
        
        [xmin, ymin] = np.int32(all_pts.min(axis=0).ravel() - 0.5)
        [xmax, ymax] = np.int32(all_pts.max(axis=0).ravel() + 0.5)
        
        t = [-xmin if xmin < 0 else 0, -ymin if ymin < 0 else 0]
        
        canvas_w = min(8000, max(xmax - xmin, w1 + t[0]))
        canvas_h = min(8000, max(ymax - ymin, h1 + t[1]))
        
        Ht = np.array([[1, 0, t[0]], [0, 1, t[1]], [0, 0, 1]])
        result = cv.warpPerspective(img_right, Ht.dot(H), (canvas_w, canvas_h))

        y1 = t[1]
        y2 = min(h1 + t[1], canvas_h)
        x1 = t[0]
        x2 = min(w1 + t[0], canvas_w)

        roi = result[y1:y2, x1:x2]
        
        crop_h = y2 - y1
        crop_w = x2 - x1
        
        mask_cropped = mask_left[0:crop_h, 0:crop_w]
        img_left_cropped = img_left[0:crop_h, 0:crop_w]
        mask_inv = cv.bitwise_not(mask_cropped)
        
        bg = cv.bitwise_and(roi, roi, mask=mask_inv)
        fg = cv.bitwise_and(img_left_cropped, img_left_cropped, mask=mask_cropped)
        
        result[y1:y2, x1:x2] = cv.add(bg, fg)

        return result
    else:
        return None

def create_mode1_display(imgs):
    sift = cv.SIFT_create()
    bf = cv.BFMatcher()
    
    h_max = max([im.shape[0] for im in imgs])
    w_total = sum([im.shape[1] for im in imgs])
    canvas = np.zeros((h_max, w_total, 3), dtype=np.uint8)
    
    x_offset = 0
    offsets = []
    kps, dess = [], []
    
    for im in imgs:
        h, w = im.shape[:2]
        canvas[0:h, x_offset:x_offset+w] = im
        offsets.append(x_offset)
        x_offset += w
        
        kp, des = sift.detectAndCompute(im, None)
        kps.append(kp)
        dess.append(des)
        
    for i in range(len(imgs)-1):
        matches = bf.knnMatch(dess[i], dess[i+1], k=2)
        good = []
        for match in matches:
            if len(match) == 2:
                m, n = match
                if m.distance < 0.75 * n.distance:
                    good.append(m)
                
        for m in good:
            pt1 = kps[i][m.queryIdx].pt
            pt2 = kps[i+1][m.trainIdx].pt
            
            x1 = int(pt1[0] + offsets[i])
            y1 = int(pt1[1])
            x2 = int(pt2[0] + offsets[i+1])
            y2 = int(pt2[1])
            
            color = tuple(np.random.randint(0, 255, 3).tolist())
            cv.line(canvas, (x1, y1), (x2, y2), color, 1)
            cv.circle(canvas, (x1, y1), 3, color, -1)
            cv.circle(canvas, (x2, y2), 3, color, -1)
            
    return canvas

def resize_for_display(img, max_height=800):
    h, w = img.shape[:2]
    if h > max_height:
        return cv.resize(img, (int(w * (max_height / h)), max_height), interpolation=cv.INTER_AREA)
    return img

if __name__ == '__main__':
    path = os.path.join(os.path.expanduser("~"), "Desktop")
    data_path = f"{path}\\data"
    
    imgs = []
    i = 1
    while True:
        img_file = os.path.join(data_path, f"image_stitching{i}.jpg")
        if not os.path.exists(img_file):
            break
        img = cv.imread(img_file)
        if img is not None:
            imgs.append(img)
        i += 1

    if len(imgs) < 2:
        print("최소 2장 필요")
        exit()

    mode0_height = 400
    mode0_imgs = [cv.resize(im, (int(im.shape[1] * (mode0_height / im.shape[0])), mode0_height)) for im in imgs]
    mode0_display = cv.hconcat(mode0_imgs)

    mode1_display = create_mode1_display(imgs)

    center_idx = len(imgs) // 2
    result_img = imgs[center_idx]

    for idx in range(center_idx + 1, len(imgs)):
        result_img = stitch_pair(result_img, imgs[idx])
        if result_img is None:
            print("정합 실패")
            exit()

    for idx in range(center_idx - 1, -1, -1):
        result_img = stitch_pair(result_img, imgs[idx])
        if result_img is None:
            print("정합 실패")
            exit()
            
    mode2_display = result_img

    display_mode = 0
    while True:
        if display_mode == 0:
            show_img = mode0_display.copy()
            info = "Original"
        elif display_mode == 1:
            show_img = mode1_display.copy()
            info = "Feature points matched"
        elif display_mode == 2:
            show_img = mode2_display.copy()
            info = "Stitched"
            
        show_img = resize_for_display(show_img, max_height=900)
        
        cv.putText(show_img, info, (10, 30), cv.FONT_HERSHEY_DUPLEX, 1.0, (0, 255, 0), 2)
        cv.imshow('Image Stitching Gooooooooooooooooooooooood', show_img)
        
        key = cv.waitKey(30)
        if key == 27: 
            break
        elif key == 32: 
            display_mode = (display_mode + 1) % 3
            
    cv.destroyAllWindows()
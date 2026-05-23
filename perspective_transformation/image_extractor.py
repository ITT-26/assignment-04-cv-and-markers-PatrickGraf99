import argparse
import math
import numpy as np
import cv2

WINDOW_NAME = 'Preview Window'

selected_points = []
CIRCLE_RADIUS = 5
CIRCLE_COLOR = (255, 0, 0)
CIRCLE_BORDER_SIZE = -1 # -1 for fill

cv2.namedWindow(WINDOW_NAME)

img = None
draw_image = None
path_output = None
result_img = None

target_size = None

def mouse_callback(event, x, y, flags, param):
    # Disable mouse after all points are selected
    if len(selected_points) > 3:
        return

    global img

    # USe a copy for drawing
    global draw_image

    # Append mouse click points...
    if event == cv2.EVENT_LBUTTONDOWN:
        selected_points.append((x, y))

    mark_and_show_image()

    # transform and display the final selection
    if len(selected_points) > 3:
        transform_and_display_selection()


def transform_and_display_selection():
    print('Displaying final image...')
    sorted_points = sort_selected_points_chatgpt()
    global target_size
    HEIGHT = target_size[1]
    WIDTH = target_size[0]
    # Same as in the example code from the class
    source_points = np.float32(np.array(sorted_points))
    destination_points = np.float32(np.array([[0, 0], [WIDTH, 0], [WIDTH, HEIGHT], [0, HEIGHT]]))

    # Get the matrix (again, same as in example)
    warp_matrix = cv2.getPerspectiveTransform(source_points, destination_points)

    # Transform the image, also just as in the example
    warped_image = cv2.warpPerspective(img, warp_matrix, (WIDTH, HEIGHT), flags=cv2.INTER_LINEAR)
    global result_img
    result_img = warped_image.copy()
    cv2.imshow(WINDOW_NAME, warped_image)

def sort_selected_points():
    """
    Sorts all points from top left to bottom right. The methof of figuring this out was to ask chatGPT. the implementation
    was done by myself although the autocompletion feature of PyCharm helped immensely
    """
    # Using chatGPT method  to calculate which point represents which corner
    global selected_points
    x_sum = selected_points[0][0] + selected_points[1][0] + selected_points[2][0] + selected_points[3][0]
    y_sum = selected_points[0][1] + selected_points[1][1] + selected_points[2][1] + selected_points[3][1]
    center = (x_sum / 4, y_sum / 4)
    angles = []
    for point in selected_points:
        angles.append(math.degrees(math.atan2(point[1] - center[1], point[0] - center[0])))
    matches = [(a, p) for a, p in zip(angles, selected_points)]
    # print(matches)
    # This line was interestingly enough not written by chatGPT but it was suggested from PyCharms autocompletion feature
    matches.sort(key=lambda x: x[0], reverse=True)
    print(matches)
    return matches

def sort_selected_points_chatgpt():
    """
    This method also sorts points from top left to bottom right. However, this time the code was directly copied from
    ChatGPT. This should be functionally similar to sort_selected_points() but a lot less verbose and cleaner
    (Although maybe harder to read and understand)
    """
    global selected_points
    # Calculate center point
    center_x = sum(p[0] for p in selected_points) / 4
    center_y = sum(p[1] for p in selected_points) / 4

    # Sort by angle around center
    sorted_points = sorted(
        selected_points,
        key=lambda p: math.atan2(p[1] - center_y, p[0] - center_x)
    )

    # Rotate list so top left is first
    top_left_index = min(
        range(4),
        key=lambda i: sorted_points[i][0] + sorted_points[i][1]
    )

    sorted_points = (
            sorted_points[top_left_index:] +
            sorted_points[:top_left_index]
    )

    return sorted_points

def delete_last_point():
    global selected_points
    # Disable deleting points once the final image is shown
    if len(selected_points) > 3:
        print('Can\'t delete last point as final image is already shown')
        return
    # Delete last point in list if list is not empty
    if len(selected_points) > 0:
        print('Deleting last point...')
        selected_points.pop(-1)
        mark_and_show_image()

def mark_and_show_image():
    global selected_points
    global draw_image
    # Copy image to get the basis
    draw_image = img.copy()
    # Add a circle for each selected point
    for point in selected_points:
        draw_image = cv2.circle(draw_image, (point[0], point[1]), CIRCLE_RADIUS, CIRCLE_COLOR, CIRCLE_BORDER_SIZE)
    # Redraw the image
    cv2.imshow(WINDOW_NAME, draw_image)

def reset():
    global selected_points
    selected_points = []
    mark_and_show_image()

def save_result():
    global selected_points
    # If there are currently fewer than 4 points displayed no result is shown
    if len(selected_points) <3:
        return
    global result_img
    global path_output
    print('Saving result to ' + path_output)
    cv2.imwrite(path_output, result_img)




def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--image', required=True, help='Path to image')
    parser.add_argument('-o', '--output', required=True, help='Path to save result to')
    parser.add_argument('-s', '--size', required=True, help='Target size provided in format WIDTHxHEIGHT')
    args = parser.parse_args()
    path_input = args.image
    print('Input path:', path_input)
    global path_output
    path_output = args.output
    global img
    img = cv2.imread(path_input)
    # Init size only after loading image so img is not None
    global target_size
    try:
        target_size = (int(args.size.split('x')[0]), int(args.size.split('x')[1]))
    except ValueError:
        print('Invalid size was provided for the resulting image, using same size as input has')
        target_size = (img.shape[1], img.shape[0])
    global draw_image
    draw_image = img.copy()
    cv2.imshow(WINDOW_NAME, img)
    cv2.setMouseCallback(WINDOW_NAME, mouse_callback)

    while True:
        key = cv2.waitKey(0) & 0xFF
        # print(key)

        # Exit script on q
        if key == ord('q'):
            print('Exiting program')
            break

        #  Use c to delete last point
        elif key == ord('c'):
            delete_last_point()

        elif key == ord('s'):
            save_result()

        # Manually check ord of ESCAPE
        elif key == 27:
            reset()


if __name__ == '__main__':
    main()

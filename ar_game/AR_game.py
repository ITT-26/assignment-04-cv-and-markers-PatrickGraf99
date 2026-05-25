from enum import Enum

import cv2
import pyglet
from PIL import Image
from pyglet import shapes

from ar_game.image_processor import ImageProcessor
from ar_game.image_processor import StatusCode

class GameState(Enum):
    RUNNING = 0
    PAUSED = 1
    AUTO_PAUSED = 2

class Textangle(shapes.Rectangle):
    """
    A Rectangle but it has text
    """

    def __init__(self, x, y, width, height, text, color=(0, 0, 0), highlight_color=(115, 190, 181),
                 font_name='Calibri', font_size=20):
        super().__init__(x, y, width, height, color)
        self.x = x
        self.y = y
        text_x = x + width / 2
        text_y = y + height / 2
        self.text_content = text
        self.text = pyglet.text.Label(text, font_name=font_name, font_size=font_size, x=text_x, y=text_y,
                                      anchor_x='center', anchor_y='center', align='center', multiline=True,
                                      width=int(width-40))

    def set_text(self, _text):
        self.text.text = _text

    def draw(self) -> None:
        super().draw()
        self.text.draw()

    def set_opacity(self, _opacity):
        self.opacity = _opacity



class ARGame:
    def __init__(self):
        self.WIDTH = 0
        self.HEIGHT = 0
        self.image_processor = ImageProcessor(self)
        self.frame_img = None
        self.window = None
        self.state = GameState.RUNNING
        self.cursor_x = 0
        self.cursor_y = 0
        self.player_rect = None
        self.last_known_state = GameState.RUNNING
        self.pause_screen = None

        self.fruits = []
        self.bombs = []

    def update_frame_size(self, size):
        self.WIDTH, self.HEIGHT = size[1], size[0]
        print(f'Setting game window to {self.WIDTH} x {self.HEIGHT}')

    def handle_frame_ready(self, data):
        status = data['status']
        if status == StatusCode.ARUCO_ERROR:
            self.handle_aruco_error(data['frame'])
        elif status == StatusCode.NO_CURSOR:
            self.handle_no_cursor_error(data['frame'])
        elif status == StatusCode.NO_CAM:
            self.handle_cam_error(data['frame'])
        else:
            self.handle_frame_received(data['frame'], data['cursor'][0], data['cursor'][1])

    def handle_aruco_error(self, frame):
        #print('Ran into aruco error')
        self.frame_img = self.cv2glet(frame, 'BGR')
        self.state = GameState.AUTO_PAUSED
        self.pause_screen.set_text('Could not detect the game area, please make sure the camera has a good view on the aruco markers')
        self.pause_screen.set_opacity(200)

    def handle_no_cursor_error(self, frame):
        print('Ran into no cursor error')
        self.frame_img = self.cv2glet(frame, 'BGR')
        self.state = GameState.AUTO_PAUSED
        self.pause_screen.set_text('Could not detect a cursor, please use blue tape on your finger (or any other blue object)')
        self.pause_screen.set_opacity(200)

    def handle_cam_error(self, frame):
        print('Ran into camera error')
        self.frame_img = self.cv2glet(frame, 'BGR')
        self.state = GameState.AUTO_PAUSED
        self.pause_screen.set_text('It seems we are not getting any camera footage, is your cam set up correctly?')
        self.pause_screen.set_opacity(200)

    def handle_frame_received(self, frame, x, y):
        # if game was automatically paused return to last known state
        if self.state == GameState.AUTO_PAUSED:
            self.state = self.last_known_state
            self.pause_screen.set_text('Game is paused\nPress \'SPACE\' to continue')
        print(f'Successfully received frame cursor is at {x},{y}')
        self.correct_cursor_position(x, y)
        self.frame_img = self.cv2glet(frame, 'BGR')
        self.player_rect.x = self.cursor_x
        self.player_rect.y = self.cursor_y

    def correct_cursor_position(self, x, y):
        """Who thought it was a good way to use a coordinate system that does not start at the top left in any
        it-related space??? Thanks, pyglet"""
        self.cursor_x = x
        self.cursor_y = y * -1 + self.HEIGHT



    def cv2glet(self, img, fmt):
        """Assumes image is in BGR color space. Returns a pyimg object"""
        if fmt == 'GRAY':
            rows, cols = img.shape
            channels = 1
        else:
            rows, cols, channels = img.shape

        raw_img = Image.fromarray(img).tobytes()

        top_to_bottom_flag = -1
        bytes_per_row = channels * cols
        pyimg = pyglet.image.ImageData(width=cols,
                                       height=rows,
                                       fmt=fmt,
                                       data=raw_img,
                                       pitch=top_to_bottom_flag * bytes_per_row)
        return pyimg

    def close(self):
        self.image_processor.stop()
        self.window.close()

    def handle_pause_pressed(self):
        if self.state == GameState.PAUSED:
            self.state = GameState.RUNNING
            self.last_known_state = GameState.RUNNING
        else:
            self.state = GameState.PAUSED
            self.last_known_state = GameState.PAUSED
        print(f'Set game state to {self.state}')

    def update(self, delta_time):
        #print('Requesting update from image processor')
        # Always update the image
        self.image_processor.update()

        if self.state == GameState.RUNNING:
            self.update_fruits()
            self.update_bombs()

    def update_fruits(self):
        for fruit in self.fruits:
            fruit.y -= 3
            if self.check_player_collision(fruit):
                print(f'Collision detected for fruit')
        for bomb in self.bombs:
            bomb.y -= 3

    def check_player_collision(self, game_object):
        return True if (self.player_rect.x < game_object.x < self.player_rect.x + self.player_rect.width and
                        self.player_rect.y < game_object.y < self.player_rect.y + self.player_rect.height) else False


    def draw_pause(self):
        self.pause_screen.draw()

    def run(self):
        self.window = pyglet.window.Window(self.WIDTH, self.HEIGHT)
        self.player_rect = shapes.Rectangle(self.cursor_x, self.cursor_y, 100, 10, (0, 0, 255))
        self.pause_screen = Textangle(20, 20, self.WIDTH - 40, self.HEIGHT - 40, 'Game is paused. Press \''
                                                                                 'SPACE\' to continue', (0, 0, 0))

        @self.window.event
        def on_draw():
            self.window.clear()
            if self.frame_img is not None:
                self.frame_img.blit(0, 0, 0)
            if self.state == GameState.PAUSED:
                self.draw_pause()
                return
            elif self.state == GameState.AUTO_PAUSED:
                self.draw_pause()
                return

            self.player_rect.draw()

        @self.window.event
        def on_key_press(symbol, modifiers):
            if symbol == pyglet.window.key.ESCAPE:
                self.close()
            if symbol == pyglet.window.key.SPACE:
                self.handle_pause_pressed()

        pyglet.clock.schedule_interval(self.update, 1/60)
        pyglet.app.run()



game = ARGame()
game.run()
import os
import random
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

    def __init__(self, x, y, width, height, text, color=(0, 0, 0), font_name='Calibri', font_size=20):
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
        self.score = 0
        self.score_label = None

        self.apple_img = pyglet.image.load(os.path.join('images', 'apple.png'))
        self.banana_img = pyglet.image.load(os.path.join('images', 'banana.png'))
        self.strawberry_img = pyglet.image.load(os.path.join('images', 'strawberry.png'))
        self.melon_img = pyglet.image.load(os.path.join('images', 'melon.png'))
        self.grape_img = pyglet.image.load(os.path.join('images', 'grape.png'))
        self.bomb_img = pyglet.image.load(os.path.join('images', 'bomb.png'))
        self.basket_img = pyglet.image.load(os.path.join('images', 'basket.png'))

        for image in [
            self.apple_img,
            self.banana_img,
            self.strawberry_img,
            self.melon_img,
            self.grape_img,
            self.bomb_img,
            self.basket_img
        ]:
            self.center_image(image)

    def center_image(self, image):
        image.anchor_x = image.width // 2
        image.anchor_y = image.height // 2

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
        #print('Ran into no cursor error')
        self.frame_img = self.cv2glet(frame, 'BGR')
        self.state = GameState.AUTO_PAUSED
        self.pause_screen.set_text('Could not detect a cursor, please use blue tape on your finger (or any other blue object)')
        self.pause_screen.set_opacity(200)

    def handle_cam_error(self, frame):
        #print('Ran into camera error')
        self.frame_img = self.cv2glet(frame, 'BGR')
        self.state = GameState.AUTO_PAUSED
        self.pause_screen.set_text('It seems we are not getting any camera footage, is your cam set up correctly?')
        self.pause_screen.set_opacity(200)

    def handle_frame_received(self, frame, x, y):
        # if game was automatically paused return to last known state
        if self.state == GameState.AUTO_PAUSED:
            self.state = self.last_known_state
            self.pause_screen.set_text('Game is paused\nPress \'SPACE\' to continue')
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
        # Update game objects only if the game is running
        if self.state == GameState.RUNNING:
            self.update_game_objects()

    def update_game_objects(self):
        # For all fruits, remove them if they go below canvas or handle collision if they collide with player
        to_remove = None
        for fruit in self.fruits:
            fruit.y -= 3
            if fruit.y + fruit.height < 0:
                to_remove = fruit
                break
            if self.check_player_collision(fruit):
                self.handle_fruit_collision(fruit)

        # Prevent modifying a list while iterating over it
        if to_remove is not None:
            self.fruits.remove(to_remove)

        to_remove = None
        # Same for bombs
        for bomb in self.bombs:
            bomb.y -= 3
            if bomb.y + bomb.height < 0:
                to_remove = bomb
                break
            if self.check_player_collision(bomb):
                self.handle_bomb_collision(bomb)

        if to_remove is not None:
            self.bombs.remove(to_remove)
        # Spawn new game objects if need be
        self.spawn_new_game_objects()

    def draw_game_objects(self):
        for fruit in self.fruits:
            fruit.draw()
        for bomb in self.bombs:
            bomb.draw()

    def handle_fruit_collision(self, fruit):
        self.fruits.remove(fruit)
        self.score += 1
        self.update_score_label()

    def handle_bomb_collision(self, bomb):
        self.bombs.remove(bomb)
        self.score -= 5
        self.update_score_label()

    def update_score_label(self):
        self.score_label.set_text(f'Score: {self.score}')

    def check_player_collision(self, obj):
        # Original logic by me (that means doing a standard collision check with overlapping bounding boxes and using a
        # grace area so objects do not collide on their edges)
        # ----- PLAYER HITBOX -----

        player_width = self.player_rect.image.width * self.player_rect.scale
        player_height = self.player_rect.image.height * self.player_rect.scale

        # Shrink basket collision area horizontally
        player_width *= 0.65

        # Only use lower half of basket
        player_height *= 0.35

        # Basket center
        player_left = self.player_rect.x - player_width / 2
        player_right = self.player_rect.x + player_width / 2

        # Lower-half collision zone
        player_bottom = self.player_rect.y - (player_height / 2)
        player_top = self.player_rect.y

        # ----- OBJECT HITBOX -----

        obj_width = obj.image.width * obj.scale
        obj_height = obj.image.height * obj.scale

        # Grace factor:
        # make fruit/bomb collision area smaller
        obj_width *= 0.6
        obj_height *= 0.6

        obj_left = obj.x - obj_width / 2
        obj_right = obj.x + obj_width / 2
        obj_bottom = obj.y - obj_height / 2
        obj_top = obj.y + obj_height / 2

        # ----- AABB COLLISION -----

        return (
                player_left < obj_right and
                player_right > obj_left and
                player_bottom < obj_top and
                player_top > obj_bottom
        )

    def spawn_new_game_objects(self):
        # USe random x pos and y offset to make game objects not appear in the same spot
        if len(self.fruits) < 5:
            image = random.choice([self.apple_img, self.banana_img, self.grape_img, self.melon_img, self.strawberry_img])
            randx = random.randint(50, self.WIDTH - 50)
            randy = random.randint(50, 200)
            _fruit = pyglet.sprite.Sprite(image, x=randx, y=self.HEIGHT + randy)
            _fruit.scale =.2
            self.fruits.append(_fruit)
        if len(self.bombs) < 2:
            randx = random.randint(50, self.WIDTH - 50)
            randy = random.randint(50, 200)
            _bomb = pyglet.sprite.Sprite(self.bomb_img, x=randx, y=self.HEIGHT + randy)
            _bomb.scale = .2
            self.bombs.append(_bomb)

    def draw_pause(self):
        self.pause_screen.draw()

    def run(self):
        self.window = pyglet.window.Window(self.WIDTH, self.HEIGHT)
        #self.player_rect = shapes.Rectangle(self.cursor_x, self.cursor_y, 100, 10, (0, 0, 255))
        self.player_rect = pyglet.sprite.Sprite(self.basket_img, x=self.cursor_x, y=self.cursor_y)
        self.player_rect.scale = .4
        self.pause_screen = Textangle(20, 20, self.WIDTH - 40, self.HEIGHT - 40, 'Game is paused. Press \''
                                                                                 'SPACE\' to continue', (0, 0, 0))
        self.score_label = Textangle(self.WIDTH / 2 - 100, self.HEIGHT - 60, 200, 40, f'Score: {self.score}')


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
            self.draw_game_objects()
            self.score_label.draw()

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
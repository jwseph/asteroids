from math import sin, cos, pi, radians as rad, atan2, inf
from random import randint, random, choice
import pygame
from pygame.locals import (K_UP, K_LEFT, K_RIGHT,K_DOWN, K_w, K_a, K_s, K_d, K_z, K_x, K_b, K_m, K_SPACE, K_ESCAPE, KEYDOWN, KEYUP, MOUSEBUTTONDOWN, QUIT)
from pygame import gfxdraw
from threading import Timer
import sys, os


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def distance(x1, y1, x2, y2):
    return ((x2-x1)**2+(y2-y1)**2)**0.5


def rotate(v, a, add):
    s = sin(a)
    c = cos(a)
    x, y = v
    p, q = add
    return (x*c-y*s+p, x*s+y*c+q)


def draw_line(surface, x1, y1, x2, y2, color, thickness):
    # creates line-style polygon using perpendicular points
    thickness /= 2
    angle = atan2(y2-y1, x2-x1)
    s, c = sin(angle), cos(angle)

    A = (x1 + s*thickness, SCREEN_HEIGHT - (y1 - c*thickness))
    B = (x1 - s*thickness, SCREEN_HEIGHT - (y1 + c*thickness))
    D = (x2 + s*thickness, SCREEN_HEIGHT - (y2 - c*thickness))
    C = (x2 - s*thickness, SCREEN_HEIGHT - (y2 + c*thickness))

    gfxdraw.aapolygon(surface, (A, B, C, D), color)
    gfxdraw.filled_polygon(surface, (A, B, C, D), color)


def draw_lines(add, color, width, lines):
    p, q = add
    for ((x1, y1), (x2, y2)) in lines:
        draw_line(screen, round(x1+p), round(y1+q), round(x2+p), round(y2+q), color, width)


def draw_shape(add, color, width, vertices):
    draw_lines(add, color, width, [[vertices[i], vertices[i+1]]
               for i in range(-1, len(vertices)-1)])


def draw_rotation(a, add, color, width, lines):
    p, q = add
    for ((x1, y1), (x2, y2)) in lines:
        draw_line(screen, *rotate((x1, y1), a, add), *
                  rotate((x2, y2), a, add), color, width)


def draw_text(text, size, x, y, center = True, spacing=5/8):
    n = len(text)
    if center:
        x-=(2+spacing)*(n-1)/2*size
    p, q = x, SCREEN_HEIGHT - y
    for ((x1, y1), (x2, y2)) in [[((line_x+i*(2+spacing))*size,line_y*size) for (line_x,line_y) in line] for i in range(n) for line in HYPERFONT[text[i]]]:
        draw_line(screen, round(x1+p), round(y1+q), round(x2+p), round(y2+q), FGCOLOR, TEXT_WIDTH)

        gfxdraw.box(screen, pygame.Rect(int(x1+p-TEXT_WIDTH/2), int(SCREEN_HEIGHT-y1-q-TEXT_WIDTH/2), TEXT_WIDTH*2, TEXT_WIDTH*2), FGCOLOR)
        gfxdraw.box(screen, pygame.Rect(int(x2+p-TEXT_WIDTH/2), int(SCREEN_HEIGHT-y2-q-TEXT_WIDTH/2), TEXT_WIDTH*2, TEXT_WIDTH*2), FGCOLOR)


def draw_ship(x, y):
    draw_rotation(pi/2, (x, SCREEN_HEIGHT-y), FGCOLOR, TEXT_WIDTH,
                  [[(x/2/SHIP_SIZE*32, y/2/SHIP_SIZE*32) for (x, y) in line] for line in ship.shape])


def beat():
    if asteroid_sum()>0 and ship.alive():
        Timer(60 / (60+180*(1-asteroid_sum()/(7*get_level_asteroids()))), beat).start()
        if unpaused:
            global lastBeat
            beatChannel.play(sfx[f"beat{lastBeat}"])
            lastBeat=1-lastBeat


def thrust_sound():
    if thrusting and ship.alive():
        Timer(THRUST_LENGTH-0.01, thrust_sound).start()
        if unpaused: thrustChannel.queue(sfx["thrust"])
    elif running:
        Timer(1/FPS_, thrust_sound).start()


def enemy_spawn_chance():
    if len(enemies.sprites()) == 0 and ship.alive() and ((asteroid_sum()>8 and random()<ENEMY_SPAWN[0]) or (asteroid_sum()<=8 and random()<ENEMY_SPAWN[1])):
        enemies.add(Enemy(random() < (level/9 if level < 9 else 1)))


def randfrom(a, b): return a+(b-a)*random()
def asteroid_sum(): return sum((8 >> asteroid.size)-1 for asteroid in asteroids)
def get_level_asteroids(): return level*2+2 if level*2+2 < 11 else 11
def get_sound(path): return pygame.mixer.Sound(resource_path(path))

class Entity(pygame.sprite.Sprite):
    def __init__(self, x, y, xvel, yvel, radius):
        super().__init__()
        self.x = x
        self.y = y
        self.xvel = xvel
        self.yvel = yvel
        self.radius = radius
        self.name = self.__class__.__name__
        self.isPlayerBullet = False

    def move(self, r=None):
        if r == None:
            r = self.radius

        self.x += self.xvel/FPS
        self.y += self.yvel/FPS

        if self.x < 0-r:
            self.x = SCREEN_WIDTH+r
        elif self.x > SCREEN_WIDTH+r:
            self.x = 0-r
        if self.y < 0-r:
            self.y = SCREEN_HEIGHT+r
        elif self.y > SCREEN_HEIGHT+r:
            self.y = 0-r

    def collide(self, Group_):
        return next((target for target in Group_ if distance(self.x, self.y, target.x, target.y) < self.radius+target.radius), None)

    def draw_hitbox(self):
        gfxdraw.aacircle(screen, round(self.x), round(SCREEN_HEIGHT-self.y), round(self.radius), HBCOLOR)

class Debris(Entity):

    def __init__(self, x, y, color):
        angle = 2*pi*random()
        speed = randfrom(DEBRIS_SPEED/2, DEBRIS_SPEED)
        super().__init__(x, y, cos(angle)*speed, sin(angle)*speed, 1)
        self.color = color
        self.countdown = DEBRIS_TIME*FPS+randint(-1/2*FPS, 1/2*FPS) / 2

    def update(self):
        self.xvel *= PARTICLE_MULTIPLIER
        self.yvel *= PARTICLE_MULTIPLIER
        self.move()
        self.draw()

        self.countdown -= 1
        if self.countdown <= 0:
            self.kill()

    def draw(self):
        gfxdraw.aacircle(screen, round(self.x), round(SCREEN_HEIGHT-self.y), self.radius, self.color)
        gfxdraw.filled_circle(screen, round(self.x), round(SCREEN_HEIGHT-self.y), self.radius, self.color)

    def explosion(x, y, color):
        particles.add([Debris(x, y, color) for n in range(DEBRIS_COUNT)])


class Fragment(Entity):

    def __init__(self, x, y, xvel, yvel, length, angle, turn):
        super().__init__(x, y, xvel, yvel, length/2)
        self.angle = angle
        self.turn = turn
        self.countdown = FRAGMENT_TIME*FPS+randint(-1/2*FPS, 1/2*FPS)

    def update(self):
        self.xvel *= PARTICLE_MULTIPLIER
        self.yvel *= PARTICLE_MULTIPLIER
        self.turn *= PARTICLE_MULTIPLIER
        self.angle += self.turn/FPS
        self.move()
        self.draw()

        self.countdown -= 1
        if self.countdown <= 0 and deaths < lives:
            self.kill()

    def draw(self):
        draw_rotation(self.angle, (self.x, self.y), FGCOLOR, FGWIDTH, [[(self.radius, 0), (-self.radius, 0)]])


class Bullet(Entity):

    def __init__(self, x, y, xvel, yvel, isPlayerBullet):
        super().__init__(x, y, xvel, yvel, FGWIDTH)
        self.isPlayerBullet = isPlayerBullet
        self.countdown = BULLET_TIME*FPS

    def update(self, enemies=[]):
        self.move()
        self.draw()

        self.countdown -= 1
        if self.countdown <= 0:
            self.kill()

    def draw(self):
        gfxdraw.aacircle(screen, round(self.x), round(SCREEN_HEIGHT-self.y), self.radius, FGCOLOR)
        gfxdraw.filled_circle(screen, round(self.x), round(SCREEN_HEIGHT-self.y), self.radius, FGCOLOR)

    def collide(self):
        Group_ = asteroids_ + \
            enemies_ if self.isPlayerBullet else asteroids_+players_
        target = next((target for target in Group_ if distance(self.x, self.y, target.x,
                      target.y) < self.radius+target.radius and target.name != "Bullet"), None)

        if target != None:
            self.explode()
            self.kill()

    def explode(self):
        pass


class Ship(Entity):

    def __init__(self):
        super().__init__(SCREEN_WIDTH/2, SCREEN_HEIGHT/2, 0, 0, 1/2*SHIP_SIZE/2)
        self.rot = rad(90)
        self.blinkCooldown = 0
        # total front ship angle is 34 degrees
        self.shape = [[(x*SHIP_SIZE/2, y*SHIP_SIZE/2) for (x, y) in line] for line in
                      [
            [(-0.8290375725550416, 0.5591929034707469), (1, 0)],
            [(1, 0), (-0.8290375725550416, -0.5591929034707469)],
            [(-0.6, 0.48916909033385664), (-0.6, -0.48916909033385664)]
        ]]
        self.trailShape = [[(x*SHIP_SIZE/2, y*SHIP_SIZE/2) for (x, y) in line] for line in
                           [
            [(-0.6, 0.32611272688923776), (-1.2, 0)],
            [(-1.2, 0), (-0.6, -0.32611272688923776)]
        ]]

    def update(self):
        self.blinkCooldown += 1
        if self.blinkCooldown == -1:
            self.x = randfrom(SHIP_SIZE, SCREEN_WIDTH-SHIP_SIZE)
            self.y = randfrom(SHIP_SIZE, SCREEN_HEIGHT-SHIP_SIZE)
            while(super().collide([*asteroids, *enemies]) != None):
                self.x = SHIP_SIZE+(SCREEN_WIDTH-SHIP_SIZE*2)*random()
                self.y = SHIP_SIZE+(SCREEN_HEIGHT-SHIP_SIZE*2)*random()

            if random() < HYPERSPACE:
                self.explode()
                self.kill()
                global deaths
                deaths += 1

        elif self.blinkCooldown >= 0:
            if self.blinkCooldown > 4 * FPS/60:
                self.blinkCooldown = 0

            if not mouse:
                if pressed_keys[A] or pressed_keys[K_LEFT]:
                    self.rot += TURN_SPEED/FPS
                if pressed_keys[D] or pressed_keys[K_RIGHT]:
                    self.rot -= TURN_SPEED/FPS
                self.rot %= 2*pi
            else:
                self.rot = atan2(SCREEN_HEIGHT-self.y-mouse_y, mouse_x-self.x)

            if thrusting:
                self.xvel -= (self.xvel-cos(self.rot)*MAX_SPEED)*(1/INERTIA)
                self.yvel -= (self.yvel-sin(self.rot)*MAX_SPEED)*(1/INERTIA)
            else:
                self.xvel -= self.xvel*1/FRICTION
                self.yvel -= self.yvel*1/FRICTION

            self.move(SHIP_SIZE/2)
            self.draw()

    def draw(self):
        draw_rotation(self.rot, (self.x, self.y), FGCOLOR, FGWIDTH, self.shape)
        if thrusting and self.blinkCooldown < 2 * FPS/60:
            draw_rotation(self.rot, (self.x, self.y), FGCOLOR, FGWIDTH, self.trailShape)

    def collide(self):
        target = super().collide(asteroids_+enemies_)
        if target != None:
            self.explode(target)
            self.kill()
            global deaths
            deaths += 1

    def hyperspace(self):
        self.x, self.y = SCREEN_WIDTH*2, SCREEN_HEIGHT*2
        self.xvel = self.yvel = 0
        self.blinkCooldown = -HYPERSPACE_TIME*FPS

    def explode(self, target=None):
        fragments = [[(0.2713703034306198*SHIP_SIZE, 0.06989911293384336*SHIP_SIZE), rad(-17), 1/5*pi],
              [(0.2713703034306198*SHIP_SIZE, -
                0.06989911293384336*SHIP_SIZE), rad(17), -1/5*pi],
              [(-0.18588908970814066*SHIP_SIZE,
                0.20969733880153008*SHIP_SIZE), rad(-17), 3/5*pi],
              [(-0.18588908970814066*SHIP_SIZE, -
                0.20969733880153008*SHIP_SIZE), rad(17), -3/5*pi],
              [(-0.3*SHIP_SIZE, 0), pi/2, pi]]

        if target == None:
            for fragment in fragments:
                rand = random()
                particles.add(Fragment(*rotate(fragment[0], self.rot, (self.x, self.y)), cos(self.rot+fragment[2])*FRAGMENT_SPEED*rand+self.xvel, sin(self.rot+fragment[
                              2])*FRAGMENT_SPEED*rand+self.yvel, 3/4*0.5672713369495156*SHIP_SIZE, self.rot+fragment[1], FRAGMENT_ROTATION*(randint(0, 1)*2-1)*rand))
        else:
            speed = 1/2*(self.xvel**2+self.yvel**2)**0.5
            if target.name == "Bullet":
                for fragment in fragments:
                    rand = random()
                    rotatedFragment=rotate(fragment[0], self.rot, (self.x, self.y))
                    a = atan2(rotatedFragment[1]-target.y, rotatedFragment[0]-target.x)
                    particles.add(Fragment(*rotate(fragment[0], self.rot, (self.x, self.y)),
                                  cos(self.rot+fragment[2])*FRAGMENT_SPEED *
                        rand+(cos(a)*speed)+target.xvel/2,
                        sin(self.rot+fragment[2])*FRAGMENT_SPEED *
                        rand+(sin(a)*speed)+target.yvel/2,
                        3/4*0.5672713369495156*SHIP_SIZE, self.rot+fragment[1], FRAGMENT_ROTATION*(randint(0, 1)*2-1)*rand))
            else:
                for fragment in fragments:
                    rand = random()
                    rotatedFragment=rotate(fragment[0], self.rot, (self.x, self.y))
                    a = atan2(rotatedFragment[1]-target.y, rotatedFragment[0]-target.x)
                    particles.add(Fragment(*rotate(fragment[0], self.rot, (self.x, self.y)),
                                  cos(self.rot+fragment[2])*FRAGMENT_SPEED *
                        rand+(cos(a)*speed),
                        sin(self.rot+fragment[2])*FRAGMENT_SPEED *
                        rand+(sin(a)*speed),
                        3/4*0.5672713369495156*SHIP_SIZE, self.rot+fragment[1], FRAGMENT_ROTATION*(randint(0, 1)*2-1)*rand))

        Debris.explosion(self.x, self.y, FGCOLOR)
        sfx["bangSmall"].play()


class Asteroid(Entity):

    def __init__(self, size=0, x=None, y=None):
        if size == 0:
            AS1 = randfrom(ASTEROID_RADIUS[size], 3*ASTEROID_RADIUS[size])
            AS2 = randfrom(ASTEROID_RADIUS[size], 3*ASTEROID_RADIUS[size])
            if randint(0, 1):
                x = randfrom(AS1, SCREEN_WIDTH-AS1)
                y = AS2 if randint(0, 1) else SCREEN_HEIGHT-AS2
            else:
                x = AS1 if randint(0, 1) else SCREEN_WIDTH-AS1
                y = randfrom(AS2, SCREEN_HEIGHT-AS2)
        direction = 2*pi*random()
        '''IMPORTANT!!!!!!!!!!!!!!!!!!!'''
        speed = randfrom(1/2*ASTEROID_SPEED[size], 2/2*ASTEROID_SPEED[size])
        super().__init__(x, y, cos(direction)*speed,
                         sin(direction)*speed, ASTEROID_RADIUS[size])
        self.size = size
        self.shape = [(round(x/4*self.radius), round(y/4*self.radius)) for (x, y) in
                      choice([[
                          (-4, 2), (-2, 4), (0, 2), (2, 4),
                          (4, 2), (3, 0), (4, -2), (1, -4),
                          (-2, -4), (-4, -2)
                      ], [
                          (-4, 2), (-2, 4), (0, 3), (2, 4),
                          (4, 2), (2, 1), (4, -1), (2, -4),
                          (-1, -3), (-2, -4), (-4, -2), (-3, 0)
                      ], [
                          (-4, 1), (-1, 4), (2, 4), (4, 1),
                          (4, -1), (2, -4), (0, -4), (0, -1),
                          (-2, -4), (-4, -1), (-2, 0)
                      ], [
                          (-4, 2), (-1, 2), (-2, 4), (1, 4),
                          (4, 2), (4, 1), (1, 0), (4, -2),
                          (2, -4), (1, -3), (-2, -4), (-4, -1)
                      ]])
                      ]

    def update(self):
        self.move()
        self.draw()

    def draw(self):
        draw_shape((self.x, self.y), MGCOLOR, MGWIDTH, self.shape)

    def collide(self):
        target = super().collide(players_+enemies_)
        if target != None:
            if target.isPlayerBullet:
                global points
                points += ASTEROID_POINTS[self.size]
            self.explode()
            self.kill()

    def explode(self):
        Debris.explosion(self.x, self.y, MGCOLOR)
        if self.size < 2:
            asteroids.add(Asteroid(self.size+1, self.x, self.y))
            asteroids.add(Asteroid(self.size+1, self.x, self.y))
        sfx[("bangLarge", "bangMedium", "bangSmall")[self.size]].play()
        enemy_spawn_chance()


class Enemy(Entity):

    def __init__(self, size):
        y = randfrom(ENEMY_RADIUS[size], SCREEN_HEIGHT-ENEMY_RADIUS[size])
        if randint(0, 1):
            x = -ENEMY_RADIUS[size]
            xvel = randfrom(ENEMY_SPEED[0], ENEMY_SPEED[1])
        else:
            x = SCREEN_WIDTH+ENEMY_RADIUS[size]
            xvel = -randfrom(ENEMY_SPEED[0], ENEMY_SPEED[1])
        super().__init__(x, y, xvel, 0, ENEMY_RADIUS[size])
        self.size = size
        self.actionCooldown = 0
        self.shoot = -2*ENEMY_FIRERATE*FPS

        
        self.lines = [[(round(x/5*self.radius), round(y/5*self.radius)) for (x, y) in line] for line in
                     [[(-2, 1), (-1, 3)], [(-1, 3), (1, 3)], [(1, 3), (2, 1)],
                     [(2, 1), (5, -1)], [(5, -1), (2, -3)], [(2, -3), (-2, -3)],
                     [(-2, -3), (-5, -1)], [(-5, -1), (-2, 1)], [(-2, 1), (2, 1)],
                     [(-5, -1), (5, -1)]
                     ]]

        sirenChannel.play(sfx[("saucerBig", "saucerSmall")[self.size]], -1)

    def update(self):
        self.actionCooldown += 1
        if self.actionCooldown == ENEMY_TIME*FPS:
            self.actionCooldown = 0
            self.yvel = randint(-1, 1)*randfrom(ENEMY_SPEED[0], ENEMY_SPEED[1])

        if ship.alive():
            self.shoot += 1
            if self.shoot >= ENEMY_FIRERATE*FPS:
                self.shoot = 0
                if self.size == 0:
                    a = 2*pi*random()
                    c = cos(a)
                    s = sin(a)
                else:
                    a = atan2(ship.y-self.y, ship.x-self.x)
                    offs_angle = randfrom(-pi/8, pi/8)
                    c = cos(a+offs_angle)
                    s = sin(a+offs_angle)
                enemies.add(Bullet(self.x+c*self.radius, self.y +
                            s*self.radius, c*BULLET_SPEED, s*BULLET_SPEED, False))
                sfx["saucerFire"].play()

        self.move()
        self.draw()

    def draw(self):
        draw_lines((self.x, self.y), FGCOLOR, MGWIDTH, self.lines)

    def move(self):
        self.x += self.xvel/FPS
        self.y += self.yvel/FPS

        if self.y < 0-self.radius:
            self.y = SCREEN_HEIGHT+self.radius
        elif self.y > SCREEN_HEIGHT+self.radius:
            self.y = 0-self.radius

        if self.x < 0-self.radius or self.x > SCREEN_WIDTH+self.radius:
            self.kill()
            sirenChannel.stop()

    def collide(self):
        target = super().collide(players_+asteroids_)
        if target != None:
            if target.isPlayerBullet:
                global points
                points += ENEMY_POINTS[self.size]
            self.explode()
            self.kill()
            sirenChannel.stop()

    def explode(self):
        Debris.explosion(self.x, self.y, FGCOLOR)
        sfx["bangSmall"].play()


HYPERFONT={
    '0': [[(-1,1.5),(1,1.5)], [(-1,-1.5),(1,-1.5)], [(-1,1.5),(-1,-1.5)], [(1,1.5),(1,-1.5)]],
    '1': [[(0,1.5),(0,-1.5)]],
    '2': [[(-1,1.5),(1,1.5)], [(-1,0),(1,0)], [(-1,-1.5),(1,-1.5)], [(-1,0), (-1,-1.5)], [(1,1.5),(1,0)]],
    '3': [[(-1,1.5),(1,1.5)], [(-1,0),(1,0)], [(-1,-1.5),(1,-1.5)], [(1,1.5),(1,-1.5)]],
    '4': [[(-1,0),(1,0)], [(-1,1.5),(-1,0)], [(1,1.5),(1,-1.5)]],
    '5': [[(-1,1.5),(1,1.5)], [(-1,0),(1,0)], [(-1,-1.5),(1,-1.5)], [(-1,1.5),(-1,0)], [(1,0), (1,-1.5)]],
    '6': [[(-1,0),(1,0)], [(-1,-1.5),(1,-1.5)], [(-1,1.5),(-1,-1.5)], [(1,0),(1,-1.5)]],
    '7': [[(-1,1.5),(1,1.5)], [(1,1.5),(1,-1.5)]],
    '8': [[(-1,1.5),(1,1.5)], [(-1,0),(1,0)], [(-1,-1.5),(1,-1.5)], [(-1,1.5),(-1,-1.5)], [(1,1.5),(1,-1.5)]],
    '9': [[(-1,1.5),(1,1.5)], [(-1,0),(1,0)], [(-1,1.5),(-1,0)], [(1,1.5),(1,-1.5)]],
    ' ': [],
    'A': [[(-1,1.5-2/3),(0,1.5)], [(0,1.5),(1,1.5-2/3)], [(-1,0.2),(1,0.2)], [(-1,1.5-2/3),(-1,-1.5)], [(1,1.5-2/3),(1,-1.5)]],
    'B': [[(-1,1.5),(0.5,1.5)], [(0.5,1.5),(1,1)], [(0.5,0.2),(1,0.5)], [(-1,0.2),(0.5,0.2)], [(0.5,0.2),(1,-0.5)], [(0.5,-1.5),(1,-1)], [(-1,-1.5),(0.5,-1.5)], [(-1,1.5),(-1,-1.5)], [(1,1),(1,0.5)], [(1,-0.5),(1,-1)]],
    'C': [[(-1,1.5),(1,1.5)], [(-1,-1.5),(1,-1.5)], [(-1,1.5),(-1,-1.5)]],
    'D': [[(-1,1.5),(0,1.5)], [(0,1.5),(1,0.5)], [(1,-0.5),(0,-1.5)], [(-1,-1.5),(0,-1.5)], [(-1,1.5),(-1,-1.5)], [(1,0.5),(1,-0.5)]],
    'E': [[(-1,1.5),(1,1.5)], [(-1,0.2),(1,0.2)], [(-1,-1.5),(1,-1.5)], [(-1,1.5),(-1,-1.5)]],
    'F': [[(-1,1.5),(1,1.5)], [(-1,0.2),(1,0.2)], [(-1,1.5),(-1,-1.5)]],
    'G': [[(-1,1.5),(1,1.5)], [(0,-0.5),(1,-0.5)], [(-1,-1.5),(1,-1.5)], [(-1,1.5),(-1,-1.5)], [(1,1.5),(1,0.5)], [(1,-0.5),(1,-1.5)]],
    'H': [[(-1,0.2),(1,0.2)], [(-1,1.5),(-1,-1.5)], [(1,1.5),(1,-1.5)]],
    'I': [[(-1,1.5),(1,1.5)], [(-1,-1.5),(1,-1.5)], [(0,1.5),(0,-1.5)]],
    'J': [[(-1,-0.5),(0,-1.5)], [(0,-1.5),(1,-1.5)], [(1,1.5),(1,-1.5)]],
    'K': [[(-1,0.2),(1,1.5)], [(-1,0.2),(1,-1.5)], [(-1,1.5),(-1,-1.5)]],
    'L': [[(-1,-1.5),(1,-1.5)], [(-1,1.5),(-1,-1.5)]],
    'M': [[(-1,1.5),(0,0.5)], [(0,0.5),(1,1.5)], [(-1,1.5),(-1,-1.5)], [(1,1.5),(1,-1.5)]],
    'N': [[(-1,1.5),(1,-1.5)], [(-1,1.5),(-1,-1.5)], [(1,1.5),(1,-1.5)]],
    'O': [[(-1,1.5),(1,1.5)], [(-1,-1.5),(1,-1.5)], [(-1,1.5),(-1,-1.5)], [(1,1.5),(1,-1.5)]],
    'P': [[(-1,1.5),(1,1.5)], [(-1,0.2),(1,0.2)], [(-1,1.5),(-1,-1.5)], [(1,1.5),(1,0.2)]],
    'Q': [[(-1,1.5),(1,1.5)], [(0,-1.5),(1,-0.5)], [(0,-0.5),(1,-1.5)], [(-1,-1.5),(0,-1.5)], [(-1,1.5),(-1,-1.5)], [(1,1.5),(1,-0.5)]],
    'R': [[(-1,1.5),(1,1.5)], [(-1,0.2),(1,0.2)], [(-1,0.2),(1,-1.5)], [(-1,1.5),(-1,-1.5)], [(1,1.5),(1,0.2)]],
    'S': [[(-1,1.5),(1,1.5)], [(-1,0.2),(1,0.2)], [(-1,-1.5),(1,-1.5)], [(-1,1.5),(-1,0.2)], [(1,0.2), (1,-1.5)]],
    'T': [[(-1,1.5),(1,1.5)], [(0,1.5),(0,-1.5)]],
    'U': [[(-1,-1.5),(1,-1.5)], [(-1,1.5),(-1,-1.5)], [(1,1.5),(1,-1.5)]],
    'V': [[(-1,1.5),(0,-1.5)], [(0,-1.5),(1,1.5)]],
    'W': [[(-1,-1.5),(0,-0.5)], [(0,-0.5),(1,-1.5)], [(-1,1.5),(-1,-1.5)], [(1,1.5), (1,-1.5)]],
    'X': [[(-1,1.5),(1,-1.5)], [(1,1.5),(-1,-1.5)]],
    'Y': [[(-1,1.5),(0,0.5)], [(0,0.5),(1,1.5)], [(0,0.5),(0,-1.5)]],
    'Z': [[(-1,1.5),(1,1.5)], [(-1,-1.5),(1,-1.5)], [(1,1.5),(-1,-1.5)]],
    '_': [[(-1,-1.5),(1,-1.5)]]
    }

# region Constants
W, A, S, D = K_w, K_a, K_s, K_d

FGCOLOR = (255, 255, 255)
MGCOLOR = (150, 150, 150)  # was (100,100,100)
BGCOLOR = (0, 0, 0)
HBCOLOR = (0, 255, 255)  # hitbox color

pygame.init()
displayInfo = pygame.display.Info()
MONITOR_WIDTH = displayInfo.current_w
MONITOR_HEIGHT = displayInfo.current_h - 40 - 32
if MONITOR_WIDTH / 36 > MONITOR_HEIGHT / 25:
    SHIP_SIZE = int(MONITOR_HEIGHT / 25 // 2) * 2
else:
    SHIP_SIZE = int(MONITOR_WIDTH / 36 // 2) * 2
print(SHIP_SIZE)
SCREEN_WIDTH, SCREEN_HEIGHT = SHIP_SIZE*36, SHIP_SIZE*25

FPS_ = 60
TEXT_WIDTH = 1
FGWIDTH = 2  # 2
MGWIDTH = 1  # 1

FRICTION = 200
INERTIA = round(1/(1-(1-1/60)**(60/FPS_)))  # 60
MAX_SPEED = 17*SHIP_SIZE  # 17
TURN_SPEED = rad(225)  # radians per second
HYPERSPACE = 0.1
HYPERSPACE_TIME = 1
RELOAD = 4
REVIVE_TIME = 3
LIVES = 3

BULLET_SPEED = 17*SHIP_SIZE  # 17
BULLET_TIME = 1.2

# 0 is big, 1 is medium, 2 is small
ASTEROID_SPEED = (4*SHIP_SIZE, 5.25*SHIP_SIZE, 6.5*SHIP_SIZE)
ASTEROID_RADIUS = (1.2*SHIP_SIZE, 0.6*SHIP_SIZE, 0.3*SHIP_SIZE)

# 0 is big, 1 is small
ENEMY_RADIUS = (SHIP_SIZE*0.75, SHIP_SIZE*0.375)
ENEMY_SPEED = (4*SHIP_SIZE, 6.5*SHIP_SIZE)
ENEMY_TIME = 1
ENEMY_FIRERATE = 0.5
ENEMY_SPAWN = (0.1, 0.4) # see enemy_spawn_chance()

PARTICLE_MULTIPLIER = 0.99
FRAGMENT_ROTATION = rad(180)  # radians per second
FRAGMENT_TIME = 2.5  # seconds
FRAGMENT_SPEED = 1*SHIP_SIZE
DEBRIS_COUNT = 12
DEBRIS_TIME = 0.5
DEBRIS_SPEED = 5*SHIP_SIZE

LEVEL_TIME = 3
DEATH_TIME = 7

ASTEROID_POINTS = (20, 50, 100)
ENEMY_POINTS = (200, 1000)

KONAMI_CODE = [K_UP, K_UP, K_DOWN, K_DOWN, K_LEFT, K_RIGHT, K_LEFT, K_RIGHT, K_b, K_a]
# endregion

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_icon(pygame.image.load(resource_path("icon.png")))
clock = pygame.time.Clock()

pygame.mixer.init()
pygame.mixer.set_num_channels(22)
sounds = ["fire", "thrust", "beat0", "beat1", "extraShip",
          "bangLarge", "bangMedium", "bangSmall", "saucerBig", "saucerSmall", "saucerFire"]
sfx = {sound: get_sound(f"{sound}.wav") for sound in sounds}
THRUST_LENGTH = sfx["thrust"].get_length()
thrustChannel = pygame.mixer.Channel(19)
sirenChannel = pygame.mixer.Channel(20)
beatChannel = pygame.mixer.Channel(21)
thrusting=None

players = pygame.sprite.Group()
asteroids = pygame.sprite.Group()
enemies = pygame.sprite.Group()
particles = pygame.sprite.Group()
running = True
thrust_sound()
showHitboxes = False
showAsteroidSum = False
points = ""
konami = False
mouse = False

while running:
    pygame.display.set_caption("Asteroids - 62.5 fps")
    game = True
    thrusting = False
    level = 1
    levelCooldown = 0
    reviveCooldown = 0
    deaths = 0
    lives = LIVES
    thrustTimer = 0
    unpaused = True
    konamiIndex = 0


    # region Starting Menu
    FPS = inf
    screen.fill(BGCOLOR)
    asteroids.add([Asteroid() for n in range(get_level_asteroids())])
    levelCooldown -= 1
    pygame.display.flip()

    toggleText = 0
    while toggleText != None:
        screen.fill(BGCOLOR)
        for entity in (*asteroids, *enemies, *players):
            entity.update()
            if showHitboxes:
                gfxdraw.aacircle(screen, round(entity.x), round(
                    SCREEN_HEIGHT-entity.y), round(entity.radius), HBCOLOR)
        draw_text(str(points).ljust(6, ' '), 8, 28, 32, False)
        if showAsteroidSum:
            draw_text(str(asteroid_sum()).rjust(6, ' '),
                      8, SCREEN_WIDTH-(105+28), 32, False)
        draw_text("ASTEROIDS", 20, SCREEN_WIDTH/2,
                  SCREEN_HEIGHT*1/2-28+16, spacing=1/2)
        if toggleText >= 0:
            draw_text("PRESS SPACE TO PLAY", 4, SCREEN_WIDTH/2,
                      SCREEN_HEIGHT*1/2+28+16, spacing=1)
        pygame.display.flip()
        clock.tick_busy_loop(20)
        toggleText += 1/20
        if toggleText >= 1:
            toggleText = -1

        for event in pygame.event.get():
            if event.type == KEYDOWN:
                if event.key == K_SPACE:
                    toggleText = None
                if event.key == K_z:
                    showHitboxes = not showHitboxes
                if event.key == K_x:
                    showAsteroidSum = not showAsteroidSum
                if event.key == K_m:
                    mouse = not mouse
            if event.type == MOUSEBUTTONDOWN:
                toggleText = None
            if event.type == QUIT:
                toggleText = None
                running = False

    FPS = FPS_
    points = 0
    # endregion

    ship = Ship()
    players.add(ship)
    lastBeat = 0
    beat()

    while (game or not pressed_keys[K_SPACE]) and running:
        
        for event in pygame.event.get():
            if event.type == KEYDOWN and event.key == K_SPACE or event.type == MOUSEBUTTONDOWN:
                if not (ship.alive() and len(players.sprites())-1 < RELOAD+2*RELOAD*konami*2+RELOAD*konami and unpaused):
                    continue
                players.add(Bullet(ship.x+ship.radius*cos(ship.rot), ship.y+ship.radius*sin(
                    ship.rot), cos(ship.rot)*BULLET_SPEED+ship.xvel, sin(ship.rot)*BULLET_SPEED+ship.yvel, True))
                if konami:
                    players.add(Bullet(sin(ship.rot)*ship.radius+ship.x+ship.radius/3*cos(ship.rot), -cos(ship.rot)*ship.radius+ship.y+ship.radius/3*sin(
                        ship.rot), cos(ship.rot-pi/12)*BULLET_SPEED+ship.xvel, sin(ship.rot-pi/12)*BULLET_SPEED+ship.yvel, True))
                    players.add(Bullet(-sin(ship.rot)*ship.radius+ship.x+ship.radius/3*cos(ship.rot), cos(ship.rot)*ship.radius+ship.y+ship.radius/3*sin(
                        ship.rot), cos(ship.rot+pi/12)*BULLET_SPEED+ship.xvel, sin(ship.rot+pi/12)*BULLET_SPEED+ship.yvel, True))
                sfx["fire"].play()
            if event.type == KEYDOWN:
                if event.key == W or event.key == K_UP:
                    if ship.alive() and ship.blinkCooldown >= 0 and unpaused:
                        thrusting = True
                elif event.key == K_z:
                    showHitboxes = not showHitboxes
                elif event.key == K_x:
                    showAsteroidSum = not showAsteroidSum
                elif event.key == K_m:
                    mouse = not mouse
                elif event.key == K_ESCAPE:
                    unpaused = not unpaused
                    if unpaused:
                        pygame.mixer.unpause()
                    else:
                        pygame.mixer.pause()
                elif event.key == S or event.key == K_DOWN:
                    # blinkCooldown is <0 when ship is in hyperspace
                    if ship.blinkCooldown >= 0 and ship.alive() and unpaused:
                        ship.hyperspace()
                
                if event.key == KONAMI_CODE[konamiIndex]:
                    konamiIndex += 1
                    if konamiIndex == 10:
                        konamiIndex = 0
                        konami = not konami
                else:
                    if not (konamiIndex == 2 and event.key == K_UP):
                        konamiIndex = int(event.key == K_UP)

            elif event.type == KEYUP:
                if event.key == W or event.key == K_UP:
                    if unpaused:
                        thrusting = False
            elif event.type == QUIT:
                running = False


        if lives < LIVES+points//10000:
            lives = LIVES+points//10000
            sfx["extraShip"].play()
        if not ship.alive() and unpaused:
            if reviveCooldown < REVIVE_TIME*FPS:
                reviveCooldown += 1
            if reviveCooldown >= REVIVE_TIME*FPS and next((False for entity in asteroids.sprites()+enemies.sprites() if distance(entity.x, entity.y, SCREEN_WIDTH/2, SCREEN_HEIGHT/2) < entity.radius+16*ship.radius), True):
                if deaths < lives:
                    ship.__init__()
                    players.add(ship)
                    beat()
                    enemies.empty()
                    sirenChannel.stop()
                    reviveCooldown = 0
                else:
                    game = False
        
        if len(asteroids.sprites())+len(enemies.sprites()) == 0:
            if levelCooldown == -1:
                level += 1
                levelCooldown = LEVEL_TIME*FPS
            elif levelCooldown == 0:
                asteroids.add([Asteroid()
                              for n in range(get_level_asteroids())])
                lastBeat = 0
                beat()
            levelCooldown -= 1
        

        pressed_keys = pygame.key.get_pressed()
        mouse_x, mouse_y = pygame.mouse.get_pos()

        screen.fill(BGCOLOR)
        if unpaused:
            for entity in [*asteroids, *particles, *enemies, *players]:
                entity.update()
                if showHitboxes:
                    entity.draw_hitbox()
        else:
            for entity in [*asteroids, *particles, *enemies, *players]:
                entity.draw()
                if showHitboxes: entity.draw_hitbox()
        
        if showHitboxes and not ship.alive():
            gfxdraw.aacircle(screen, SCREEN_WIDTH//2, SCREEN_HEIGHT//2, round(16*ship.radius), HBCOLOR)

        players_ = players.sprites()
        enemies_ = enemies.sprites()
        asteroids_ = asteroids.sprites()
        for entity in players_+enemies_+asteroids_:
            entity.collide()

        draw_text(str(points).ljust(6, ' '), 8, 28, 32, False)
        if showAsteroidSum:
            draw_text(str(asteroid_sum()).rjust(6, ' '),
                      8, SCREEN_WIDTH-(105+28), 32, False)
        for n in range(lives-deaths):
            draw_ship(24-3/4*8/4+12*n, 60) # 11/8

        if not game:
            draw_text("GAME OVER", 20, SCREEN_WIDTH /
                      2, SCREEN_HEIGHT/2, spacing=1/2)

        pygame.display.flip()
        clock.tick_busy_loop(FPS)
        pygame.display.set_caption(f"Asteroids - {clock.get_fps()} fps")

    players.empty()
    asteroids.empty()
    enemies.empty()
    particles.empty()
    sirenChannel.stop()

pygame.quit()
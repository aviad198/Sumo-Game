from machine import Pin, I2C, PWM
import ssd1306
import time
import urandom
import math
from time import sleep_ms

# Initialize I2C interface
i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)

# Initialize SSD1306 OLED display
display = ssd1306.SSD1306_I2C(128, 64, i2c)

# Initialize buzzer
buzzer_pin = Pin(23, Pin.OUT)
buzzer_pwm = PWM(buzzer_pin)
buzzer_pwm.duty(0)

# Initialize button
button = Pin(4, Pin.IN, Pin.PULL_UP)

# Define constants
SUMO_RADIUS = 14
SUMO_SPEED = 2
GAME_WIDTH = 128
GAME_HEIGHT = 64
BORDER_THICKNESS = 2
song = [(500, 659), (500, 659), (500, 659), (500, 523), (500, 587), (500, 587)]

# Sumo pixel map
sumo_pixels = [
    "00000000000000000000",
    "00000000011000000000",
    "00000000111100000000",
    "00000001111110000000",
    "00000001100110000000",
    "00000111100111100000",
    "00001101100110110000",
    "00011101111100111000",
    "00111000111100011100",
    "00110000000000001100",
    "00110011000011001100",
    "00111011000011011100",
    "00011111111111111000",
    "00001111111111110000",
    "00000100111100100000",
    "00000100100100100000",
    "00000111100111100000",
    "00000011000011000000",
    "00000000000000000000",
    "00000000000000000000"
]

class Sumo:
    def __init__(self, position, angle):
        self.position = position
        self.angle = angle
        self.moving = False
        self.pushing = False
        self.pattern = sumo_pixels
    
    def draw(self, bw):
        sumo_x = int(self.position[0])
        sumo_y = int(self.position[1])
        # roate
        self.pattern = rotate_pattern(self.angle)
        # Draw the Sumo
        for i, row in enumerate(self.pattern):
            for j, pixel in enumerate(row):
                if pixel == '1':
                    display.pixel(sumo_x + j, sumo_y + i, bw)
        # Draw direction indicator if moving
        if not self.moving:
            # Increment angle by 10 degrees
            self.angle += 20
            if self.angle >= 360:
                self.angle = 0

    def move(self, other_sumo):
        if not button.value():
            self.moving = True
            self.angle += SUMO_SPEED
            self.position[0] = int(self.position[0] + (SUMO_RADIUS/2) * math.cos(math.radians(self.angle)))
            self.position[1] = int(self.position[1] + (SUMO_RADIUS/2) * math.sin(math.radians(self.angle)))
            self.push(other_sumo)
        else:
            self.moving = False
            

    def push(self, other_sumo):
        # Calculate the distance between the centers of the two sumos
        sumo1_center_x, sumo1_center_y = get_sumo_center(self.position)
        sumo2_center_x, sumo2_center_y = get_sumo_center(other_sumo.position)
        distance = math.sqrt((sumo2_center_x - sumo1_center_x) ** 2 + (sumo2_center_y - sumo1_center_y) ** 2)
    
        # Check if the sumos are colliding and if self is moving towards other_sumo
        if distance <= ((2 * SUMO_RADIUS) - 10) and self.moving:
            # Calculate the direction vector from self to other_sumo
            direction_vector = [sumo2_center_x - sumo1_center_x, sumo2_center_y - sumo1_center_y]
            direction_angle = math.degrees(math.atan2(direction_vector[1], direction_vector[0]))
            # Calculate the angle difference between the sumo's movement direction and the direction to other_sumo
            angle_difference = abs(self.angle - direction_angle)
            if angle_difference > 180:
                angle_difference = 360 - angle_difference

            # Calculate the force of the push
            force = SUMO_SPEED * 1.1  # Adjust as needed

            # Calculate the components of the force
            force_x = (SUMO_RADIUS/4) * force * math.cos(math.radians(direction_angle))
            force_y = (SUMO_RADIUS/4) * force * math.sin(math.radians(direction_angle))

            if direction_vector[0] < 0:
                force_x = -abs(force_x)
            else:
                force_x = abs(force_x)
            if direction_vector[1] < 0:
                force_y = -abs(force_y)
            else:
                force_y = abs(force_y)

            # Apply the force to the other sumo
            other_sumo.position[0] += force_x
            other_sumo.position[1] += force_y
            
                  

class ComputerSumo(Sumo):
    def __init__(self, position, angle):
        super().__init__(position, angle)
        self.attack_next_spin = False

    def move(self, player_sumo):
        if self.attack_next_spin and is_computer_looking_at_player(player_sumo.position, self.position, self.angle):
            # Charge the player
            self.moving = True
            self.angle += SUMO_SPEED
            self.position[0] = int(self.position[0] + SUMO_RADIUS * math.cos(math.radians(self.angle)))
            self.position[1] = int(self.position[1] + SUMO_RADIUS * math.sin(math.radians(self.angle)))
            super().push(player_sumo)
        else:
            self.moving = False
            
    def charge_player_if_attacking(self):
        if  not self.attack_next_spin and urandom.randint(1, 100) <= 20:
            self.attack_next_spin = True
        

def buzz(duration_ms, frequency):
    buzzer_pwm.freq(frequency)  # Set the PWM frequency
    buzzer_pwm.duty(512)        # Set the PWM duty cycle (50% for a beep)
    sleep_ms(duration_ms)
    buzzer_pwm.duty(0)


# Function to play the melody
def play_song(melody):
    for duration, frequency in melody:
        if not button.value():
            return
        buzz(duration, frequency)
        

# Function to rotate the pattern by a given angle
def rotate_pattern(angle):
    rotated_pattern = []
    for i in range(len(sumo_pixels)):
        rotated_row = ""
        for j in range(len(sumo_pixels[0])):
            x = int(10 + (i - 10) * math.cos(math.radians(angle)) - (j - 10) * math.sin(math.radians(angle)))
            y = int(10 + (i - 10) * math.sin(math.radians(angle)) + (j - 10) * math.cos(math.radians(angle)))
            if 0 <= x < 20 and 0 <= y < 20:
                rotated_row += sumo_pixels[y][x]
            else:
                rotated_row += '0'
        rotated_pattern.append(rotated_row)
    return rotated_pattern


def get_sumo_center(sumo_position):
    return sumo_position[0] + 10, sumo_position[1] + 10


def is_computer_looking_at_player(player_position, computer_position, computer_angle):
    # Calculate the center coordinates of the computer sumo
    computer_center_x, computer_center_y = get_sumo_center(computer_position)
    player_center_x, player_center_y = get_sumo_center(player_position)
    # Calculate the vector from the computer sumo to the player sumo
    player_vector = [player_center_x - computer_center_x, player_center_y - computer_center_y]

    # Calculate the angle between the computer sumo's direction and the vector to the player sumo
    angle_to_player = math.degrees(math.atan2(player_vector[1], player_vector[0]))

    # Normalize the angle to be between 0 and 360 degrees
    angle_to_player = (angle_to_player + 360) % 360

    # Calculate the difference in angles between the computer sumo's direction and the angle to the player sumo
    angle_difference = abs(computer_angle - angle_to_player)

    # Ensure the angle difference is within 180 degrees
    if angle_difference > 180:
        angle_difference = 360 - angle_difference

    # If the angle difference is within a certain threshold, consider the computer sumo to be looking at the player sumo
    return angle_difference < 15  # Adjust the threshold as needed


# Function to check out of game border
def check_out(sumo):
    sumo_left = sumo.position[0]
    sumo_right = sumo.position[0] + 19
    sumo_top = sumo.position[1]
    sumo_bottom = sumo.position[1] + 19
    # Check if the player or computer sumo hits the border
    if sumo_left <= 0 or sumo_right >= GAME_WIDTH or sumo_top <= 0 or sumo_bottom >= GAME_HEIGHT:
        buzzer_pwm.freq(2000)
        buzzer_pwm.duty(512)
        time.sleep(0.5)
        buzzer_pwm.duty(0)
        # Clear display
        display.fill(0)
        return True
    return False

def draw_border():
    # Draw top border
    display.fill_rect(0, 0, GAME_WIDTH, BORDER_THICKNESS, 1)
    # Draw bottom border
    display.fill_rect(0, GAME_HEIGHT - BORDER_THICKNESS, GAME_WIDTH, BORDER_THICKNESS, 1)
    # Draw left border
    display.fill_rect(0, BORDER_THICKNESS, BORDER_THICKNESS, GAME_HEIGHT - 2 * BORDER_THICKNESS, 1)
    # Draw right border
    display.fill_rect(GAME_WIDTH - BORDER_THICKNESS, BORDER_THICKNESS, BORDER_THICKNESS, GAME_HEIGHT - 2 * BORDER_THICKNESS, 1)

def game_play(player_sumo, computer_sumo):
    time.sleep(0.5)
    while True:  
        # Clear display
        display.fill(0)
        draw_border()
        player_sumo.moving = False
        computer_sumo.moving = False
        
        computer_sumo.charge_player_if_attacking()
        
        # Move player sumo
        player_sumo.move(computer_sumo)
        # Move computer sumo
        computer_sumo.move(player_sumo)
        
        # Draw player sumo
        player_sumo.draw(1)

        # Draw computer sumo
        computer_sumo.draw(1)
        # Update display
        display.show()
        # Check collision
        if check_out(player_sumo):
            # Play buzzer sound
            display.text("ESP32 Wins!", 20, (GAME_WIDTH // 3), 1)
            display.show()
            time.sleep(2)
            return False
        elif check_out(computer_sumo):
            display.text("You Win!", 20, (GAME_WIDTH // 3), 1)
            display.show()
            time.sleep(2)
            return True



def play_sumo_game():
    while True:
        player_score = 0
        computer_score = 0
        play_rounds = 3
        for round_num in range(3):
            display.fill(1)
            display.text(f"Player:{player_score}", 5, (GAME_HEIGHT // 3) - 10 , 0)
            display.text(f"ESP32:{computer_score}", 5, (GAME_HEIGHT // 3) , 0)
            display.text(f"Round:{round_num+1}", 5, (GAME_HEIGHT // 3) + 10 , 0)
            display.text("Hold to start", 10, GAME_HEIGHT - 10 , 0)
            display_sumo = Sumo([(3 * GAME_WIDTH // 4) -10, (GAME_HEIGHT // 2) -10], 90)
            display_sumo.draw(0)
            display.show()
            play_song(song)
            while button.value():
                pass
            # Variables to track game state
            player_sumo = Sumo([(GAME_WIDTH // 4) -10, (GAME_HEIGHT // 2) - 10], 0)
            computer_sumo = ComputerSumo([(3 * GAME_WIDTH // 4) -10, (GAME_HEIGHT // 2) -10], 180) 
            result = game_play(player_sumo, computer_sumo)
            if result:
                player_score += 1
            else:
                computer_score += 1
        if player_score > computer_score:
            win_text = "Winner!!!"
        else:
            win_text = "You Lost :("
        display.fill(1)
        display.text(f"{win_text}!", 20, (GAME_WIDTH // 3), 0)
        display.show()
        time.sleep(2)
            
    
        
play_sumo_game()

    

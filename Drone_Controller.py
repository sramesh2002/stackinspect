from Drone_Class import Drone, Simulated_Drone_Realistic_Physics, Simulated_Drone_Simple_Physics, Real_Drone_Realistic_Physics
import time
import threading
#from mouse_and_keyboard_helper_functions import mouse_relative_position_from_center_normalized
#from mouse_and_keyboard_helper_functions import on_press, on_release, start_listening
import numpy as np
import matplotlib.pyplot as plt
from scipy import odr
import math
import threading
import keyboard

def key_press_thread():
    while True:
        event = keyboard.read_event()
        if event.name == "w":
            print("w pressed")
            key_pitch = 0.2
        if event.name == "a":
            print("a pressed")
            key_roll = -0.2
            time.sleep(.5)
        elif event.name == "s":
            print("s pressed")
            key_pitch = -0.2
            time.sleep(.5)
        elif event.name == "d":
            print("d pressed")
            key_roll = 0.2
            time.sleep(.5)


# Define the linear function for ODR
def linear_function(params, x):
    m, c = params
    return m * x + c

def point_line_distance(x0, y0, m, b):
    return abs(m * x0 - y0 + b) / math.sqrt(m**2 + 1)

def distancegui(point1, point2):
    """Calculate the distance between two points."""
    return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)

def dot_product(v1, v2):
    return v1[0] * v2[0] + v1[1] * v2[1]

def scalar_multiply(v, scalar):
    return (v[0] * scalar, v[1] * scalar)

def vector_subtract(v1, v2):
    return (v1[0] - v2[0], v1[1] - v2[1])

mouse_position_normalized_to_meters_velocity = 1

class Drone_Controller:
    def __init__(self, target_distance):
        self.target_distance = target_distance
        #print(type(self.target_distance))
        #print(type(self.target_distance[0]))
        self.target_angle = 90      # the target angle between the drone
        self.velocity_x_setpoint = 0
        self.velocity_y_setpoint = 0
        self.distance_error = None
    
    def get_target_drone_roll_pitch_yaw_thrust_pid(self, drone, closest_point_relative):
        # Find the displacement between the drone and the closest point
        delta_x = closest_point_relative.x_relative_distance_m
        delta_y = closest_point_relative.y_relative_distance_m

        distance = closest_point_relative.total_relative_distance_m

        # Scale this distance to a unit vector
        delta_x_unit = delta_x / distance
        delta_y_unit = delta_y / distance

        derivative_error = 0
        distance_error_prev = self.distance_error
        self.distance_error = distance - self.target_distance

        if (distance_error_prev != None):
            derivative_error = self.distance_error - distance_error_prev
        
        Kp = 2#1
        Kd = 12#8#5

        # put in the PID setpoint that is in line with the displacement to the closest point
        self.velocity_x_setpoint = delta_x_unit * (Kp * self.distance_error + Kd * derivative_error)
        self.velocity_y_setpoint = delta_y_unit * (Kp * self.distance_error + Kd * derivative_error)

        K_YAW_CTRL = 50

        current_yaw = drone.get_current_yaw_angle()
        target_yaw = current_yaw + closest_point_relative.lidar_angle_degrees
        error_yaw = target_yaw - current_yaw
        while (abs(error_yaw) > 180):
            if error_yaw > 0:
                error_yaw -= 360
            else:
                error_yaw += 360

        error_yaw = error_yaw * K_YAW_CTRL / 100

        setpoint_yaw1 = (current_yaw + error_yaw + 360) % 360

        return [self.velocity_x_setpoint, self.velocity_y_setpoint, setpoint_yaw1, 0.5]
        # return [0,0,0,0.5]
    def get_target_drone_velocity(self, drone, closest_point_relative):

        """git status

        # Get the mouse input so we can move the drone perpendicular to the line between nearest point & drone
        mouse_x, mouse_y = 0, 0#mouse_relative_position_from_center_normalized()

        # Calculate the projection of (mouse_x, mouse_y) onto (delta_x_unit, delta_y_unit)
        projection_scale = dot_product((mouse_x, mouse_y), (delta_x_unit, delta_y_unit))
        projection = scalar_multiply((delta_x_unit, delta_y_unit), projection_scale)

        # Subtract the projection from the original vector to get the perpendicular component
        perpendicular_component = vector_subtract((mouse_x, mouse_y), projection)

        # Add the mouse component onto the setpoint (perpendicular to the dist between closest point & drone)
        """

        print("keyroll: " + str(key_roll), "keypitch: " + str(key_pitch))
        self.velocity_x_setpoint += key_roll
        self.velocity_y_setpoint += key_pitch

        # Hover thrust ranges from 0 to 1
        # Mouse_Y ranges from -1 to 1
        hover_thrust_range_fraction = 0.5
        hover_thrust_setpoint = 0.5 + mouse_y * hover_thrust_range_fraction / 2
        # TODO: add a feature to allow the user to fix the hover thrust at a particular level

        # Update the drone's velocity using defaults for yaw and throttle
        
        #self.Drone.set_attitude_setpoint(self.velocity_x_setpoint, self.velocity_y_setpoint, setpoint_yaw1, hover_thrust_setpoint)

        #self.closest_point = closest_point
        self.error_yaw = error_yaw

        # drone_app.set_attitude_setpoint(tuple(x * mouse_position_normalized_to_meters_velocity for x in mouse_relative_position_from_center_normalized()))

    def find_closest_point(self):
        lidar_readings = self.Drone.lidar_and_wall_sim_with_gui.lidar_readings

        # we are actually all looking at relative readings
        # drone_location_meters = self.Drone.drone_location_meters

        min_distance = None
        closest_point = None

        for lidar_reading in lidar_readings:
            if min_distance is None or lidar_reading.total_relative_distance_m < min_distance:
                if (not (lidar_reading.angle>50 and lidar_reading.angle<=60)) and (not (lidar_reading.angle>135 and lidar_reading.angle<=145)) and (not (lidar_reading.angle>215 and lidar_reading.angle<=225)) and (not (lidar_reading.angle>300 and lidar_reading.angle<=310)):
                    min_distance = lidar_reading.total_relative_distance_m
                    closest_point = lidar_reading
        
        return (closest_point)

def run_simulation(drone_app):
    """
    Run the simulation of the drone, updating its position and displaying LIDAR data.

    Args:
        drone_app (Simulated_Drone_Simple_Physics): The drone application instance.
    """
    timestep = 0.1
    drone_controller.Drone.update_lidar_readings()

    # TODO GET THE KEY PRESSES AGAIN HERE
    # Bind the on_key_press function to the key press event
    #drone_app.lidar_and_wall_sim_with_gui.bind("<KeyPress>", on_key_press)
    # Set the focus to the canvas to receive keyboard events
    #drone_app.lidar_and_wall_sim_with_gui.focus_set()

    # Bind the on_command_entry_key_release method to the command_entry widget
    # drone_app.lidar_and_wall_sim_with_gui.command_entry.bind("<KeyRelease>", drone_app.lidar_and_wall_sim_with_gui.on_command_entry_key_release)


    
    while True:
        drone_controller.update_drone_velocity()

        # TODO: add drone_app.input_buffer
        # TODO: It is not getting updated on the key press, fix this
        # print(drone_app.input_buffer)
        
        print("A: {0:10.3f} D: {1:10.3f}, R: {2:10.3f}, P: {3:10.3f}, Y: {4:10.3f}".format(
            drone_controller.closest_point.lidar_angle_degrees,
            drone_controller.closest_point.total_relative_distance_m,
            drone_controller.velocity_x_setpoint,
            drone_controller.velocity_y_setpoint,
            drone_controller.error_yaw
        ))
        
        

        #drone_controller.Drone.set_attitude_setpoint(0, 0)
        #scaled_mouse_velocity = tuple(x * mouse_position_normalized_to_meters_velocity for x in mouse_relative_position_from_center_normalized())
        #drone_app.set_attitude_setpoint(scaled_mouse_velocity[0], scaled_mouse_velocity[1])
        
        time.sleep(timestep)

        drone_controller.Drone.update_location_meters(timestep)
        #print(f"iter {i}: Pre update_lidar_readings: ", type(drone_controller.Drone))
        drone_controller.Drone.update_lidar_readings()
        #lidar_readings = drone_controller.Drone.lidar_and_wall_sim_with_gui.lidar_readings
        # drone_controller.Drone.wipe_gui()
        # drone_controller.draw_perceived_wall()
        # drone_controller.Drone.lidar_and_wall_sim_with_gui.add_text(
        #     f'{drone_app.input_buffer}\n'
        #     f'Altitude: {drone_controller.Drone.drone_location_meters[2]:.1f}m\n'
        #     f'Mode: {"mode1"}')
        # drone_controller.Drone.update_gui()
        


if __name__ == '__main__':
    # Define the starting and ending meters coordinates of the wall
    walls = [   Wall((-4, -4), (-4, 4)),
                Wall((-4, 4), (0, 4)),
                Wall((0, 4), (0, 8)),
                Wall((0, 8), (6, 8)),
                Wall((6, 8), (6, -8)),
                Wall((6, -8), (0, -8)),
                Wall((0, -8), (0, -4)),
                Wall((0, -4), (-4, -4))   ]

    # Define the initial meters coordinates of the drone
    drone_location_meters = (0, 0, 0)

    # Define the standard deviation of the LIDAR noise in meters units
    lidar_noise_meters_standard_dev = 0.05
    # Define the initial yaw angle of the drone in degrees (not used in this example)
    drone_yaw_degrees = 90

    # Create a simulated drone object with simple physics
    # TODO note: simulated drone with the derivative is jumpy, this is OK, whatever
    #lidar_and_wall_sim_with_gui = Lidar_and_Wall_Simulator_With_GUI(walls, lidar_noise_meters_standard_dev)
    # TODO pass in the lidar_and_wall_sim_with_gui to the drone object
    # TODO drone_location_meters is in the drone itself
    drone_app = Simulated_Drone_Simple_Physics(walls, drone_location_meters, drone_yaw_degrees, lidar_noise_meters_standard_dev)
    #drone_app = Simulated_Drone_Realistic_Physics(walls, drone_location_meters, drone_yaw_degrees, lidar_noise_meters_standard_dev)
    #drone_app = Real_Drone_Realistic_Physics(walls, drone_location_meters, drone_yaw_degrees, lidar_noise_meters_standard_dev)

    drone_controller = Drone_Controller(drone_app)

    # Start a new thread to run the simulation, updating the drone's position and LIDAR data
    move_drone_thread = threading.Thread(target=run_simulation, args=(drone_controller.Drone,))
    # Set the thread as a daemon thread so it will automatically exit when the main program exits
    move_drone_thread.daemon = True
    # Start the simulation thread
    move_drone_thread.start()


    # start the keyboard listener thread
    t = threading.Thread(target=key_press_thread)
    t.start()

    # Run the main event loop of the drone application (Tkinter GUI)
    run_simulation(drone_app)
    #drone_controller.Drone.lidar_and_wall_sim_with_gui.mainloop()
"""
File: map.py
Programmers: Fernando Rodriguez, Charles Davis, Paul Rogers
"""
# TODO: Abstract tiles into a class holding tile_type and if the tile is hovered over

import pygame

# Constants
import src.colors as colors
from src.constants import *

# Classes
from src.grid import Grid
from src.unit import Unit

class Map:
    """
    The surface on which gameplay occurs.
    
    Comprised of a grid of tiles, where each tile
    has a tile_type and a unit_type. Units move
    across tiles and are affected by tile_type.

    """

    def __init__(self, screen, player_num):
        """
        Set up tile grid and units.

        
        Arguments:
            screen {pygame.Surface} -- The main display window
            player_num {int} -- The player identifier; 1 or 2
        """

        self.screen = screen
        self.player_num = player_num

        # The grid is a 2D array with columns and rows
        self.grid = Grid()
        cols = self.grid.cols
        rows = self.grid.rows

        # TODO: create function to return a tile, and one to get tile based on mouse_position

        # The dimensions of each tile
        self.tile_w = TILE_WIDTH
        self.tile_h = TILE_HEIGHT
        self.margin = TILE_MARGIN

        # Full map size in pixels (calculated from grid and tile sizes)
        map_w = (cols * (self.tile_w + self.margin)) + self.margin
        map_h = (rows * (self.tile_h + self.margin)) + self.margin
        self.map_size = (map_w, map_h)

        # Determine placement of map within display window
        map_x = (self.screen.get_size()[0] // 2) - (self.map_size[0] // 2)
        map_y = (self.screen.get_size()[1] // 2) - (self.map_size[1] // 2)
        map_rect = pygame.Rect(map_x, map_y, map_w, map_h)

        # Create map surface
        self.surface = self.screen.subsurface(map_rect)

        # Keep track of unit that was last clicked on
        # and last tile hovered over
        self.selected_unit = None
        self.hover_location = None

        # Set up player units
        self.all_units = []
        self.players_units = []
        self.enemy_units = []
        self.initialize_units()
        

    def handle_hover(self, mouse_position):
        """
        Highlight tile hovered over by user.
        """
        if self.mouse_position_inside_map(mouse_position):
            # Record position of hovered tile
            tile_col, tile_row = self.determine_tile_from_mouse_position(mouse_position)
            self.hover_location = (tile_col, tile_row)
        else:
            # Remove hover if off map
            self.hover_location = None

    def handle_click(self, mouse_position, turn):
        """
        Process user clicks on game tiles.
        TODO: Separate different levels of abstraction into separate methods.

        Arguments:
            mouse_position {(float, float)} -- The (x, y) position of mouse on window
            turn {dict} -- Contains keys move and attack. Both are lists: [unit_type, col, row]
        """

        if not self.mouse_position_inside_map(mouse_position):
            return turn

        clicked_column, clicked_row = self.determine_tile_from_mouse_position(mouse_position)
        print("[Debug]: Click", mouse_position, "Grid coords:", clicked_column, clicked_row)

        clicked_unit = None
        for unit in self.players_units:
            if unit.pos == [clicked_column, clicked_row]:
                clicked_unit = unit

        # Player hasn't moved yet
        if turn["phase"] == SELECT_UNIT_TO_MOVE:
            if clicked_unit:
                self.highlight_tiles(clicked_unit, "move")
                self.selected_unit = clicked_unit
                turn["phase"] = MOVING

        # Player has clicked unit to move
        elif turn["phase"] == MOVING:
            if self.grid.tile_in_move_range(clicked_column, clicked_row):
                movable_unit = self.selected_unit
                # Allow user to click on self to back out of moving
                if movable_unit.pos == [clicked_column, clicked_row]:
                    turn["phase"] = SELECT_UNIT_TO_MOVE
                else:
                    move = self.move(movable_unit, clicked_column, clicked_row)
                    if move:
                        turn["move"] = move
                        turn["phase"] = ATTACKING
                        # Highlight attackable tiles if enemy is in attack range
                        if self.enemy_in_attack_range():
                            self.highlight_tiles(movable_unit, "attack")
                        else:
                            self.selected_unit = None
                            turn["phase"] = END_TURN
                    else:
                        # Move is invalid, allow client to select another unit to move
                        turn["phase"] = SELECT_UNIT_TO_MOVE

                self.remove_highlight("move")
                
        # Player is attacking
        elif turn["phase"] == ATTACKING:
            # If user clicks on self, forfeit attack
            if not self.selected_unit.pos == [clicked_column, clicked_row]:
                turn["attack"] = self.attack(clicked_column, clicked_row)
            turn["phase"] = END_TURN
            self.remove_highlight("attack")
            self.selected_unit = None

        return turn

    def move(self, unit, col, row):
        """
        Move unit to given location if possible.

        Arguments:
            unit {Unit} -- The unit to move
            col {int}   -- A column on the grid
            row {int}   -- A row on the grid
        """
        move = None
        if unit:
            if self.grid.get_unit_type(col, row) == 0:
                # Set old tile to unit_type of blank
                self.grid.set_unit_type(unit.col(), unit.row(), 0)
                # Update grid with new unit position
                self.grid.set_unit_type(col, row, unit.type)
                unit.pos = [col, row]
                move = [unit.type, col, row]

        return move

    def attack(self, col, row):
        """
        Attack another unit at given col, row.
        """
        attack = None
        if self.grid.tile_in_attack_range(col, row):
            for enemy_unit in self.enemy_units:
                if enemy_unit.pos == [col, row]:
                    self.selected_unit.attack(enemy_unit)
                    if not enemy_unit.is_alive:
                        self.kill_unit(enemy_unit)
                    attack = [enemy_unit.type, self.selected_unit.attack_power]
        return attack

    def determine_tile_from_mouse_position(self, mouse_position):
        """
        To get position relative to map, we must subtract the
        offset from the mouse position. Dividing by the tile
        size gives us the clicked tile.
        
        Arguments:
            mouse_position {(float, float)} -- Position (x, y) of mouse on game window in pixels

        Returns:
            tile_position {(int, int)} -- Column and row of tile on grid
        """
        mouse_x, mouse_y = mouse_position
        offset_x, offset_y = self.get_rect().topleft

        col = (mouse_x - offset_x) // (self.tile_w + self.margin)
        row = (mouse_y - offset_y) // (self.tile_h + self.margin)

        return (col, row)

    def highlight_tiles(self, unit, range_type):
        if range_type == "move":
            tile_type = 3
        elif range_type == "attack":
            tile_type = 4
        movable_list = unit.get_range(range_type, self.grid.cols, self.grid.rows)
        print(movable_list)
        for position in movable_list:
            col = position[0]
            row = position[1]
            self.grid.set_tile_type(col, row, tile_type)

    def remove_highlight(self, range_type):
        if range_type == "move":
            highlight_type = 3
        elif range_type == "attack":
            highlight_type = 4
        for row in range(self.grid.rows):
            for col in range(self.grid.cols):
                tile_type = self.grid.get_tile_type(col, row)
                if tile_type == highlight_type:
                    self.grid.set_tile_type(col, row, 0)

    def draw(self):
        """
        Draw map onto surface.
        """

        self.surface.fill(colors.white)

        # Loop through the grid data structure
        for row in range(self.grid.rows):
            for col in range(self.grid.cols):

                # Get current unit and tile
                unit_type = self.grid.get_unit_type(col, row)
                unit = None
                if unit_type != 0:
                    unit = self.get_unit_by_type(unit_type)
                tile_type = self.grid.get_tile_type(col, row)

                # Determine color of tiles
                tile_color = colors.darkgray
                if tile_type == HEALTH:
                    tile_color = colors.green
                elif tile_type == HARM:
                    tile_color = colors.red
                elif tile_type == MOVABLE:
                    tile_color = colors.yellow
                elif tile_type == ATTACKABLE:
                    tile_color = colors.purple

                # Display tiles
                tile_rect = pygame.draw.rect(self.surface,
                                        tile_color,
                                        [(self.margin + self.tile_w) * col + self.margin,
                                         (self.margin + self.tile_h) * row + self.margin,
                                         self.tile_w,
                                         self.tile_h])

                # Highlight hovered tile
                if self.hover_location:
                    if self.hover_location == (col, row):
                        pygame.draw.rect(self.surface,
                                     colors.get_hover_color(tile_color),
                                     tile_rect)


                # TODO: Draw units inside Unit class. Pass in tile_rect
                # Determine unit color and shape
                # using tile's rect as reference
                pointlist = None
                if unit:
                    if unit.is_triangle():
                        # Green triangle
                        pointlist = [
                            tile_rect.midtop,
                            tile_rect.bottomleft,
                            tile_rect.bottomright
                        ]
                    elif unit.is_diamond():
                        # Red diamond
                        pointlist = [
                            tile_rect.midtop,
                            tile_rect.midleft,
                            tile_rect.midbottom,
                            tile_rect.midright
                        ]
                    elif unit.is_circle():
                        # Blue circle
                        pos = tile_rect.center
                        radius = tile_rect.width / 2

                    # Draw unit
                    if pointlist is not None:
                        pygame.draw.polygon(
                            self.surface,
                            unit.color,
                            pointlist
                        )
                    else:
                        pygame.draw.circle(
                            self.surface,
                            unit.color,
                            pos,
                            int(radius)
                        )

    def get_rect(self):
        """
        Return rect with (x, y) relative to window.

        Returns:
            Rect -- The rectangle bounding map grid
        """

        x, y = self.surface.get_abs_offset()
        w, h = self.map_size
        return pygame.Rect(x, y, w, h)

    def get_unit_by_type(self, unit_type):
        target_unit = None

        if unit_type == 0:
            return None

        for unit in self.all_units:
            if unit.type == unit_type:
                target_unit = unit
                break
        else:
            print("[Error]: Could not get unit by type.")

        return target_unit

    def initialize_units(self):
        """
        Place all units on map in initial positions.
        """
        # Create Unit objects and add to list
        total_units = (2 * MAX_UNITS)
        for unit_type in range(1, total_units + 1):
            unit = Unit(unit_type)
            self.all_units.append(unit)

        # Determine this player's units
        for unit in self.all_units:
            if unit.is_players_unit(self.player_num):
                self.players_units.append(unit)
            else:
                self.enemy_units.append(unit)

        # Place units on grid
        left_column = 0
        right_column = self.grid.cols - 1
        top_row = 0
        middle_row = self.grid.rows // 2
        bottom_row = self.grid.rows - 1
        positions = {
            1 : (left_column, top_row),
            2 : (left_column, middle_row),
            3 : (left_column, bottom_row),
            4 : (right_column, top_row),
            5 : (right_column, middle_row),
            6 : (right_column, bottom_row)
        }
        for unit in self.all_units:
            col, row = positions[unit.type]
            unit.pos = [col, row]
            self.grid.set_unit_type(col, row, unit.type)

    def mouse_position_inside_map(self, mouse_position):
        """
        Returns true if mouse is positioned over map.
        """
        return self.get_rect().collidepoint(mouse_position)

    def enemy_in_attack_range(self):
        """
        Returns true if an enemy unit is in self.selected_unit's attack range.
        """
        is_in_range = False
        attack_range = self.selected_unit.get_range("attack", self.grid.cols, self.grid.rows)
        for enemy_unit in self.enemy_units:
            if enemy_unit.pos in attack_range:
                is_in_range = True

        return is_in_range

    def kill_unit(self, unit):
        column, row = unit.pos
        self.grid.set_unit_type(column, row, 0)
        if unit in self.all_units:
            self.all_units.remove(unit)
        if unit in self.players_units:
            self.players_units.remove(unit)
        if unit in self.enemy_units:
            self.enemy_units.remove(unit)

    def reset(self):
        """
        Initialize the map.

        Removes special tile_types and
        resets unit health and positions.
        """
        for row in range(self.grid.rows):
            for col in range(self.grid.cols):
                self.grid.set_tile_type(col, row, 0)

        self.initialize_units()

        print("[Debug]: Map reset.")

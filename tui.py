from tui.util import hide_cursor
from tui import main_scene
from tui import chat_scene
from lib import meshchat

import curses
import curses.ascii
from os import environ


def init_color_pairs():
    curses.init_pair(1, curses.COLOR_BLUE, curses.COLOR_BLACK)
    curses.init_pair(11, curses.COLOR_WHITE, curses.COLOR_BLUE)
    curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)


def set_colors():
    curses.init_color(curses.COLOR_BLACK, 20, 20, 25)
    curses.init_color(curses.COLOR_BLUE, 120, 180, 240)
    curses.init_color(curses.COLOR_CYAN, 150, 240, 240)
    curses.init_color(curses.COLOR_GREEN, 10, 220, 10)


def render_border(win):
    win_height, win_width = win.getmaxyx()

    win.attrset(curses.color_pair(2) | curses.A_BOLD)
    win.border()
    win.attrset(0)

    win.noutrefresh()
    return curses.newwin(win_height-2, win_width-2, 1, 1)


def main(stdscr: 'curses._CursesWindow'):
    mc = meshchat.Meshchat()

    stdscr.erase()

    hide_cursor()

    if curses.can_change_color():
        set_colors()
    if curses.has_colors():
        init_color_pairs()

    canvas = render_border(stdscr)
    canvas.attrset(curses.color_pair(1) | curses.A_BOLD)

    main_scene.render(canvas, mc)
    # connection established
    chat_scene.render(canvas, mc)


if __name__ == "__main__":
    # reducing delay of the esc key for input mode switch
    environ.setdefault('ESCDELAY', '0')

    # mc.create_keys()

    curses.wrapper(main)

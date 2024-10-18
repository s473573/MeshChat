from .util import (show_cursor, hide_cursor)

import sys
import curses
import curses.ascii
from typing import List


def render_title(win):
    title = """\
    __  ___          __    ________          __ 
   /  |/  /__  _____/ /_  / ____/ /_  ____ _/ /_
  / /|_/ / _ \/ ___/ __ \/ /   / __ \/ __ `/ __/
 / /  / /  __(__  ) / / / /___/ / / / /_/ / /_  
/_/  /_/\___/____/_/ /_/\____/_/ /_/\__,_/\__/  """
    title_lines = title.splitlines()

    win_height, win_width = win.getmaxyx()
    ver_margin = int(win_height * 0.1)
    hor_margin = win_width//2 - len(title_lines[0])//2
    for i, line in enumerate(title_lines, ver_margin):
        win.addstr(i, hor_margin, line, curses.color_pair(2) | curses.A_BOLD)

    win.noutrefresh()
    return win.derwin(win_height-i-ver_margin, win_width-hor_margin, i+ver_margin, hor_margin)


def run_menu(win: 'curses._CursesWindow', items: List[str]) -> int:
    """
    Render and control a generic menu.

    :param curses._CursesWindow win: window to render to
    :param List[str] items: list of string to build items from
    :returns: index of the selected item or -1 if the user escaped
    """
    def draw_menu():
        win_height, win_width = win.getmaxyx()
        selected_item = sel_it*3+1

        i = 1
        for item in items:
            text_offset = (win_width//2 - len(item)//2)

            if i == selected_item:
                win.attron(curses.color_pair(11) | curses.A_BOLD)
            else:
                win.attroff(curses.color_pair(11) | curses.A_BOLD)

            win.addstr(i-1, 0, ' '*win_width*3)
            win.addstr(i, 0, ' '*text_offset + item.upper())

            i += 3

    win.refresh()

    sel_it = 0
    draw_menu()

    win.keypad(True)

    while (key := win.getch()) != ord('o'):
        if key == ord('j'):
            sel_it = ((sel_it+1) % len(items))
            draw_menu()
        elif key == ord('k'):
            sel_it = ((sel_it-1) % len(items))
            draw_menu()
        elif key == ord('q'):
            return -1

    win.keypad(False)

    return sel_it


def render(canvas: 'curses._CursesWindow', mc_api):
    def run_main_menu():
        menu_actions = [connect_menu, join_prompt, host]
        while True:
            info_win.erase()
            info_win.refresh()

            selected_item = run_menu(win=info_win, items=["connect", "join", "host"])
            if selected_item == -1:
                sys.exit()

            # connect menu can return -1 if the user escaped
            if menu_actions[selected_item]() != -1:
                break 

    def connect(ipa: str):
        canvas.erase()
        canvas.addstr(canvas_height//2, canvas_width//2-6, "Connecting..")
        canvas.refresh()
        mc_api.connect_network(ipa)

    def connect_menu():
        known_networks = mc_api.get_known_networks()
        if known_networks:
            si = run_menu(win=info_win, items=known_networks)
            if si == -1:
                return -1
            connect(known_networks[si])
        else:
            info_win.erase()
            info_win.addstr(iw_height-1, 0, "You don't know any networks")
            info_win.getch()
            return -1

    def join_prompt():
        info_win.addstr(iw_height-1, 0, "Enter the ip address of the inviting node: ")

        curses.echo()
        show_cursor()
        info_win.attrset(0)

        ipa = info_win.getstr()

        hide_cursor()
        curses.noecho()

        connect(ipa.decode())

    def host():
        canvas.erase()
        canvas.addstr(canvas_height//2, canvas_width//2-10, "Waiting for client..")
        canvas.refresh()

        mc_api.create_network()

    canvas_height, canvas_width = canvas.getmaxyx()

    title_win = render_title(canvas)
    title_height, title_width = title_win.getmaxyx()

    iw_hor_margin = int(canvas_width*0.1)
    info_win = canvas.derwin(canvas_height - title_height, canvas_width - iw_hor_margin*2, title_height, iw_hor_margin)
    iw_height, iw_width = info_win.getmaxyx()

    run_main_menu()

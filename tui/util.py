import curses


def hide_cursor():
    # some terminals have problem with hiding cursor
    try:
        curses.curs_set(False)
    except curses.error:
        pass


def show_cursor():
    try:
        curses.curs_set(True)
    except curses.error:
        pass

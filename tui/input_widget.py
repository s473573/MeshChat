import curses
import curses.ascii
# from time import sleep


class InputWidget:
    """A curses widget with multiline vim-keyed editing support"""

    op_keys = [curses.KEY_UP, curses.KEY_DOWN, curses.KEY_LEFT, curses.KEY_RIGHT, curses.KEY_BACKSPACE]
    nmode_keys = [ord('k'), ord('j'), ord('h'), ord('l'), ord('^'), ord('$')]

    def __init__(self, win, pad=None, lock=None):
        self.win = win

        self.text_pad = pad
        if self.text_pad is None:
            win_h, win_w = win.getmaxyx()
            self.text_pad = curses.newpad(win_h*8, win_w)

        # vertical position from which to draw the text pad
        self.pad_pos = 0
        self.curs_pos = (0, 0)

        self.lock = lock

    def get_text(self, win) -> str:
        """
        Return a window's text

        :returns: A string consisting of non-empty lines divided by newline character
        """

        lines = []
        j = 0
        # for entire text_pad it is quite slow!
        for i in range(0, win.getmaxyx()[0]):
            line = win.instr(i, 0).decode().rstrip()
            if line:
                j = i
            # else:
            #     # line = ' '
            #     line = ''
            lines.append(line)
        return '\n'.join(lines[:j+1])

    def _delete_key(self):
        cp = self.curs_pos
        target_pos = cp

        # to wrap delete
        if cp[1] == 0 and cp[0] > 0:
            self.win.insch(cp[0]-1, self.win.getmaxyx()[1]-1, " ")
            self.text_pad.insch(cp[0]-1+self.pad_pos, self.win.getmaxyx()[1]-1, " ")

            target_pos = (cp[0] - 1, self.win.getmaxyx()[1]-1)

        elif cp[1] != 0:
            # shifting all right chars one to the left
            for i in range(cp[1], self.win.getmaxyx()[1]):
                ch = self.win.inch(cp[0], i)

                self.win.addch(cp[0], i-1, ch)
                self.text_pad.addch(cp[0]+self.pad_pos, i-1, ch)
            target_pos = (cp[0], cp[1]-1)

        self.win.move(target_pos[0], target_pos[1])
        self.text_pad.move(target_pos[0]+self.pad_pos, 0)

    def _move_hor(self, dir: int):
        cp = self.curs_pos

        if 0 <= (cp[1]+dir) < self.win.getmaxyx()[1]:
            self.win.move(cp[0], cp[1]+dir)

    def _move_ver(self, dir: int):
        def ver_bound_move():
            line, column = self.curs_pos
            win_y, win_x = self.win.getbegyx()

            self.text_pad.refresh(self.pad_pos, 0, win_y, win_x, win_y+win_h-1, win_x+win_w-1)
            # to restore cursor pos after refresh
            self.win.move(line, column)

        win_h, win_w = self.win.getmaxyx()
        # can scroll pad
        if (dir < 0 and self.pad_pos > 0 and self.curs_pos[0] == 0)\
                or (dir > 0 and self.pad_pos < self.text_pad.getmaxyx()[0] and self.curs_pos[0] == (win_h-1)):
            self.pad_pos += dir
            ver_bound_move()
        # cursor within the window
        elif 0 <= (self.curs_pos[0]+dir) < win_h:
            self.win.move(self.curs_pos[0]+dir, self.curs_pos[1])

    def edit(self) -> str:
        """
        Begin editing window's text 

        :return: The string of entered text with left padding spaces
        """
        # width of the pad will always be equal to width of the window
        curses.echo(False)

        self.win.keypad(True)
        self.win.erase()

        self.text_pad.erase()

        NORMAL_MODE = False
        while (key := self.win.getch()) != ord('\n'):
            self.curs_pos = self.win.getyx()

            if key == curses.ascii.ESC:
                NORMAL_MODE = True
                continue
            elif key == ord('i') and NORMAL_MODE:
                NORMAL_MODE = False
                continue

            if key in self.op_keys or (key in self.nmode_keys and NORMAL_MODE):

                if key == curses.KEY_BACKSPACE:
                    self._delete_key()
                elif key == curses.KEY_DOWN:
                    self._move_ver(+1)
                elif key == curses.KEY_UP:
                    self._move_ver(-1)
                elif key == curses.KEY_LEFT:
                    self._move_hor(-1)
                elif key == curses.KEY_RIGHT:
                    self._move_hor(+1)

                if NORMAL_MODE:
                    if key == ord('j'):
                        self._move_ver(+1)
                    elif key == ord('k'):
                        self._move_ver(-1)
                    elif key == ord('h'):
                        self._move_hor(-1)
                    elif key == ord('l'):
                        self._move_hor(+1)

                    elif key == ord('^'):
                        self.win.move(self.curs_pos[0], 0)
                    elif key == ord('$'):
                        self.win.move(self.curs_pos[0], self.win.getmaxyx()[1]-1)

            elif not NORMAL_MODE:
                self.text_pad.addch(self.curs_pos[0]+self.pad_pos, self.curs_pos[1], key)

                if self.curs_pos[0] == self.win.getmaxyx()[0]-1 and self.curs_pos[1] == self.win.getmaxyx()[1]-1:
                    self._move_ver(+1)
                    self.win.move(self.curs_pos[0], 0)
                else:
                    self.win.addch(key)

        curses.echo(True)

        return self.get_text(self.text_pad)

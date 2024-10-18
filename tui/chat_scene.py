from .util import (show_cursor)
from .input_widget import InputWidget
from .chat_widget import ChatWidget

import curses
from threading import Thread


def render_input_bar(canvas):
    canvas_height, canvas_width = canvas.getmaxyx()

    ib_h = int(canvas_height*0.1)
    ib_hor_offset = int(canvas_width*0.1)

    input_win = canvas.derwin(ib_h, canvas_width-ib_hor_offset*2, canvas_height-ib_h, ib_hor_offset)

    input_win.bkgdset(' ', curses.color_pair(11))
    input_win.attroff(curses.A_BOLD)

    input_win.refresh()
    input_win.move(0, 0)
    return input_win


def render_messages_win(canvas):
    input_win = render_input_bar(canvas)

    canvas_y, canvas_x = canvas.getbegyx()
    canvas_height, canvas_width = canvas.getmaxyx() 

    input_pad = curses.newpad(int(canvas.getmaxyx()[0]*0.6), input_win.getmaxyx()[1])
    input_pad.bkgdset(' ', curses.color_pair(11))
    input_widg = InputWidget(input_win, input_pad)

    msgs_board = curses.newpad(canvas_height, canvas_width)
    msgs_board.attrset(curses.color_pair(11) | curses.A_BOLD)
    chat_widg = ChatWidget(canvas.derwin(input_widg.win.getbegyx()[0]-canvas_y, canvas_width, 0, 0), msgs_board)

    return (input_widg, chat_widg)


# ceiling centered ipa of node chatting with
def render(canvas, mc_api):
    def render_remote_messages():
        while (rmsg := mc_api.receive_message()) != "bye":
            if rmsg != '':
                chat_widg.render_rmsg(rmsg)
                # rendermsg moves cursor, hence restoring it, plain getbegyx wouldn't care about borders
                y, x = input_widg.win.getparyx()
                canvas.move(y, x)
                canvas.refresh()

    def chat():
        receive_thread = Thread(target=render_remote_messages)
        receive_thread.start()

        while (input_txt := input_widg.edit()) != "bye":
            if input_txt.strip() == '':
                curses.echo(False)
                curses.curs_set(0)

                # hiding input window
                chat_widg.msg_pad.refresh(chat_widg.pad_offset, 0, canvas_y, canvas_x, canvas_height, canvas_width)
                while (key := canvas.getch()) != ord('q'):
                    if key == ord('j'):
                        chat_widg.scroll_board(+1, canvas_height)
                    elif key == ord('k'):
                        chat_widg.scroll_board(-1, canvas_height)

                curses.curs_set(1)
                curses.echo(True)
            else:
                chat_widg.render_omsg(input_txt)
                mc_api.send_message(input_txt)

        receive_thread.join()

    canvas.erase()
    canvas.refresh()

    canvas_y, canvas_x = canvas.getbegyx()
    canvas_height, canvas_width = canvas.getmaxyx()

    input_widg, chat_widg = render_messages_win(canvas)
    show_cursor()

    chat()

    canvas.refresh()

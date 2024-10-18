from lib.meshchat import Meshchat

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.button import Button
from kivy.uix.label import Label
# from kivy.graphics.context_instructions import Translate
# from kivy.graphics.vertex_instructions import Rectangle
# from kivy.graphics.context_instructions import Color
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.boxlayout import BoxLayout

from functools import partial
# from threading import Thread


class StartScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_enter(self):
        self.keyboard = Window.request_keyboard(self.keyboard_closed, self)
        self.keyboard.bind(on_key_down=self.on_key_down)

    def on_touch_down(self, touch):
        touch.grab(self)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            if (touch.x - touch.ox) > 100:
                self.manager.transition.direction = 'right'
                self.manager.current = 'host'

            elif (touch.ox - touch.x) > 100:
                self.manager.transition.direction = 'left'
                self.manager.current = 'join'

    def keyboard_closed(self):
        self.keyboard.unbind(on_key_down=self.on_key_down)
        self.keyboard = None

    def on_key_down(self, keyboard, keycode, *args):
        if keycode[1] == 'h':
            self.manager.transition.direction = 'right'
            self.manager.current = 'host'
        if keycode[1] == 'j':
            self.manager.transition.direction = 'left'
            self.manager.current = 'join'
        if keycode[0] == 27:
            App.get_running_app().stop()

        return True


class HostScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_enter(self):
        Clock.schedule_once(self.host)
        self.manager.current = 'peer'

    def host(self, _):
        # Thread(target=self.manager.mc.start_network).start()
        self.manager.mc.start_network()


class JoinScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    # * would enter only once, rendering now to reduce computational load
    def on_enter(self):
        # input field to enter new ipa

        Clock.schedule_once(self.render)

    def render(self, _):
        def render_networks(_):
            nonlocal i
            if i == kn_len: return False

            n = known_networks[i]
            self.ids.known_networks.add_widget(
                Button(text=n, on_press=partial(self.connect, n)))

            i += 1

        known_networks = self.manager.mc.get_known_networks()
        kn_len = len(known_networks)
        i = 0

        Clock.schedule_interval(render_networks, 0)

    def connect(self, ipa, _):
        # Clock.schedule_once(partial(self._connect, ipa))
        self.manager.mc.join_network(ipa)
        self.manager.current = 'peer'


class ChatScreen(Screen):
    def __init__(self, mc, **kwargs):
        super().__init__(**kwargs)
        self.mc = mc

        self.decorate_message_dispatcher()

    def decorate_message_dispatcher(self):
        def chatscreen_wrapper(msg):
            dispatcher(msg)
            self.render_message(msg)

        dispatcher = self.mc.connections[self.name].dispatcher
        self.mc.set_message_dispatcher(self.name, chatscreen_wrapper)

    def on_enter(self):
        Window.bind(on_key_down=self.on_key_down)

        Clock.schedule_once(self.render)

    def render(self, _):
        self.ids.peer_label.text = self.name

    def render_message(self, msg):
        print("IMMMMMM RENDDUUUURRIIIIINGG")
        self.ids.message_layout.add_widget(Label(text=msg))

    def submit_message(self, message, _):
        self.mc.send_message(self.name, message)

        self.ids.message_layout.add_widget(Label(text=message))

    def on_key_down(self, _is, _kb, keycode, _, modifiers):
        text_input = self.ids.message_input
        if keycode == 41 and not text_input.focus:
            self.manager.current = 'peer'
            return True
        if not text_input.focus:
            return False

        if not modifiers and keycode == 40:
            Clock.schedule_once(partial(self.submit_message, text_input.text))
            text_input.text = ''
            return True
        if 'shift' in modifiers and keycode == 40:
            text_input.insert_text('\n')
            return True

    def on_leave(self):
        Window.unbind(on_key_down=self.on_key_down)


class PeerWidget(BoxLayout):
    def __init__(self, peer, on_press, **kwargs):
        super().__init__(**kwargs)

        pubkey = peer[1]
        ipa = peer[0]

        self.ids.peer_pubkey.text = pubkey.decode()

        self.ids.chat_button.text = ipa
        self.ids.chat_button.on_press = on_press


class PeerScreen(Screen):
    def __init__(self, mc, **kwargs):
        super().__init__(**kwargs)
        self.peer_widgets = dict()
        self.mc = mc

        # Clock.schedule_once(self.render)
        self.mc.bind(
            on_connected=self.handle_connection,
            on_peer_connected=self.handle_connection,
            on_peer_joined=self.render_knownpeer,
            on_peer_disconnected=self.erase_connection,
            on_received_peers=self.render
            )

    def on_enter(self):
        Window.bind(on_key_down=self.on_key_down)

    def render(self, _):
        # def render_connections(_):
        #     nonlocal i
        #     if i == cs_len: return False

        #     node = connections.pop()
        #     self.handle_connection(node)

        #     i += 1

        def render_known(_):
            nonlocal j
            if j == kp_len: return False

            peer = known_peers.pop()
            if peer[0] not in self.mc.connections:
                self.render_knownpeer(peer)

            j += 1

        # connections = self.mc.get_connections()
        # cs_len = len(connections)
        # i = 0
        # Clock.schedule_interval(render_connections, 0)

        known_peers = self.mc.get_known_peers()
        kp_len = len(known_peers)
        j = 0
        Clock.schedule_interval(render_known, 0)

    def handle_connection(self, node):
        ipa = node.peer_ipa

        self.render_connection(node)
        self.mc.set_message_dispatcher(ipa, partial(self.handle_lastmsg, node.peer_kbytes))

        assert not self.manager.has_screen(ipa)

        self.manager.add_widget(ChatScreen(self.mc, name=ipa))

    def handle_lastmsg(self, kbytes, msg):
        self.peer_widgets[kbytes].ids.last_msg.text = msg

    def render_connection(self, node):
        ipa = node.peer_ipa
        kbytes = node.peer_kbytes

        self.render_knownpeer((ipa, kbytes))
        self.peer_widgets[kbytes].ids.last_msg.text = "connected"

    def erase_connection(self, node):
        pw = self.peer_widgets[node.peer_kbytes]
        pw.ids.last_msg.text = "not connected"

        self.manager.remove_widget(self.manager.get_screen(node.peer_ipa))

    def render_knownpeer(self, peer):
        if peer[1] not in self.peer_widgets:
            peer_widget = PeerWidget(peer, partial(self.start_chat, peer[0]))

            self.peer_widgets[peer[1]] = peer_widget
            self.ids.peer_layout.add_widget(peer_widget)

    def start_chat(self, ipa):
        if not self.manager.has_screen(ipa):
            self.mc.connect_peer(ipa)
        else:
            self.manager.current = ipa

    def on_key_down(self, _is, _kb, keycode, _, modifiers):
        if keycode == 41:
            self.mc.stop()
            App.get_running_app().stop()

    def on_leave(self):
        Window.unbind(on_key_down=self.on_key_down)


class MeshchatApp(App):
    def __init__(self):
        super().__init__()
        self.mc = Meshchat()

        # * append to title user?(name/ipa/pubkey) chatting with
        # * name should be in a personal cerificate that i would get from node itself
        # * create a window with cerificate customization, avatar, name etc.
        # ? public key is the certificate's name ?
        # * in chat peer choosing screen change views to only neighbours, connected clients and all peers
        # * light up connected clients
        # * in certificate include inviter field, because of dropping the idea of prewriting known keys i can't be sure about new peers
        # ? certificate is a simple json ?

        # * you must add in advance exchange keys and write trusted key of hosting peer
        # * when in network click on node in chat screen -> add to trusted

        self.title = 'MeshChat'
        # set icon here

    def build(self):
        screen_manager = ScreenManager()
        screen_manager.mc = self.mc
        screen_manager.add_widget(StartScreen())
        screen_manager.add_widget(HostScreen(name='host'))
        screen_manager.add_widget(JoinScreen(name='join'))
        screen_manager.add_widget(PeerScreen(self.mc, name='peer'))

        return screen_manager


if __name__ == '__main__':
    Window.fullscreen = 'auto'
    MeshchatApp().run()

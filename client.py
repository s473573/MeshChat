from lib import util


if __name__ == '__main__':
    util.create_keys()

    from lib.meshchat import Meshchat
    mc = Meshchat()
    print(mc.public_bytes)

    input("Press any key...")

    known_networks = mc.get_known_networks()
    mc.join_network(known_networks[0])

    for n in mc.connections:
        mc.set_message_dispatcher(n, print)

    while True:
        ipa = input("enter ipa sending message to: ")
        msg = input("msg: ")

        mc.send_message(ipa, msg)

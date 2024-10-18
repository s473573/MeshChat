import unittest
import os

import meshchat as mc


class MeshchatTest(unittest.TestCase):
    def test_get_known_networks(self):
        ipas = ['192.168.0.1', '133.725.553', '333.333.333', '777.777.777']

        with open("known_networks", 'w') as f:
            for ipa in ipas:
                print(ipa, file=f)
        self.assertEqual(ipas, mc.get_known_networks())

        with open("known_networks", 'w') as f:
            f.write('')
        self.assertEqual([], mc.get_known_networks())

        os.remove("known_networks")
        self.assertEqual([], mc.get_known_networks())

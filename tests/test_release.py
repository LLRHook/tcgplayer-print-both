"""Test the publication boundary with generated, fictional failure inputs."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_release import scan


class PublicationTests(unittest.TestCase):
    def test_rejects_private_artifacts_without_showing_contents(self):
        for name in ['customer.pdf', 'config.json', 'ledger.sqlite3', 'browser-inputs/example.txt']:
            with self.subTest(name=name), self.assertRaises(ValueError) as caught:
                scan(name, b'private fixture contents')
            self.assertNotIn('private fixture contents', str(caught.exception))

    def test_rejects_secret_and_live_order_patterns(self):
        examples = [b'ghp_' + b'x' * 36, b'-----BEGIN ' + b'PRIVATE KEY-----', b'/Users/' + b'example/private/', b'LIVE0001' + b'-ABCDEF-12345']
        for data in examples:
            with self.subTest(kind=len(data)), self.assertRaises(ValueError):
                scan('example.txt', data)

    def test_allows_fictional_fixture_and_public_metadata(self):
        scan('example.txt', b'Order Number: TEST0001-ABCDEF-12345\nExample Customer\n123 Example Street\nExample City, VA 00000')
        scan('LICENSE', b'Copyright Victor Ivanov')


if __name__ == '__main__': unittest.main()

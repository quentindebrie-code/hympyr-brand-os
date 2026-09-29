import io
import unittest
from unittest.mock import patch
from PIL import Image

from rendering import DEFAULT_LAYERS, encode_image, render


class RenderingTest(unittest.TestCase):
    @patch('rendering.font_path', return_value=None)
    def test_template_follows_color_changes_and_exports(self, _font):
        template = {'width': 1080, 'height': 1080, 'background_token': 'V-50', 'layers': DEFAULT_LAYERS}
        fields = {'eyebrow': 'ÉNERGIES', 'title': 'Un titre qui doit tenir dans le cadre', 'body': 'Contenu vérifié.'}
        first = render(template, fields, {'V-50': '#EAF7F1'})
        updated = render(template, fields, {'V-50': '#112233'})
        self.assertEqual(first.size, (1080, 1080))
        self.assertEqual(updated.getpixel((0, 0)), (17, 34, 51))
        self.assertNotEqual(first.tobytes(), updated.tobytes())
        self.assertEqual(Image.open(io.BytesIO(encode_image(updated))).size, (1080, 1080))

    def test_logo_alpha_and_slide_order(self):
        source = Image.new('RGBA', (30, 30), (0, 0, 0, 0))
        source.putpixel((15, 15), (255, 0, 0, 255))
        logo = encode_image(source)
        template = {'width': 200, 'height': 200, 'background_token': '#FFFFFF',
                    'layers': [{'type': 'image', 'field': 'logo', 'x': 10, 'y': 10, 'width': 30, 'height': 30}]}
        output = render(template, {}, {}, lambda asset_id: logo)
        self.assertEqual(output.getpixel((10, 10)), (255, 255, 255))
        self.assertEqual(output.getpixel((25, 25)), (255, 0, 0))
        buffer = io.BytesIO()
        output.save(buffer, 'PDF', save_all=True, append_images=[output], resolution=96)
        self.assertGreater(len(buffer.getvalue()), 1000)


if __name__ == '__main__':
    unittest.main()

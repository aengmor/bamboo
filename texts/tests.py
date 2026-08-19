from django.test import TestCase
from django.urls import reverse

from .models import Character, Chapter, SlipChar, SlipText


class SlipListToggleTests(TestCase):
    def setUp(self):
        self.chapter = Chapter.objects.create(title='测试篇章', slip_order=['1'])
        self.slip = SlipText.objects.create(
            slip_id='1',
            content='测试释文',
            chapter=self.chapter,
            order=1,
        )
        self.character = Character.objects.create(
            glyph='甲',
            pronunciation='jia',
            initial='j',
            rhyme='ia',
        )
        SlipChar.objects.create(slip=self.slip, character=self.character, position=1)

    def test_slip_list_has_toggle_for_slip_id(self):
        response = self.client.get(reverse('slip_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'toggle-slip-id')
        self.assertContains(response, '显示简号')

import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory

from django.db import connection
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from .models import (
    Annotation,
    ChapterComment,
    Character,
    Chapter,
    Collection,
    CollectionComment,
    Glyph,
    GlyphAnnotation,
    SlipChar,
    Slip,
)


class SlipListToggleTests(TestCase):
    def setUp(self):
        self.chapter = Chapter.objects.create(title='测试篇章', slip_order=['1'])
        self.slip = Slip.objects.create(
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
        self.assertContains(response, 'id="app"')
        self.assertContains(response, '/static/texts/vue/assets/')

    def test_existing_detail_url_returns_vue_shell(self):
        response = self.client.get(reverse('slip_detail', args=[self.slip.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="app"')

    def test_character_detail_loads_glyphs_without_per_occurrence_queries(self):
        second_slip = Slip.objects.create(
            slip_id='2',
            content='测试释文',
            chapter=self.chapter,
            order=2,
        )
        second_character = Character.objects.create(glyph='乙')
        occurrences = [
            (self.slip, self.character, 1),
            (second_slip, second_character, 1),
        ]
        for slip, character, position in occurrences:
            SlipChar.objects.create(slip=slip, character=character, position=position)
            Glyph.objects.create(character=character, slip=slip, position=position)

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(
                reverse('character-api-occurrences', args=[self.character.pk])
            )

        glyph_queries = [query for query in queries if 'texts_glyph' in query['sql'].lower()]
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(glyph_queries), 1)

    def test_slip_api_search_is_paginated(self):
        for index in range(21):
            Slip.objects.create(
                slip_id=f'api-{index}',
                content='分页测试内容',
                chapter=self.chapter,
            )

        response = self.client.get(reverse('slip-search'), {'q': '分页测试内容'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 21)
        self.assertEqual(len(response.data['results']), 20)
        self.assertIsNotNone(response.data['next'])

    def test_slip_api_search_matches_chapter_title(self):
        response = self.client.get(reverse('slip-search'), {'q': self.chapter.title})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)

    def test_anonymous_users_cannot_write_slip_api(self):
        response = self.client.post(
            reverse('slip-list'),
            {'slip_id': 'new', 'content': '新释文'},
        )

        self.assertEqual(response.status_code, 405)

    def test_collection_detail_prefetches_slips_for_page_chapters(self):
        collection = Collection.objects.create(name='测试批次')
        self.chapter.collection = collection
        self.chapter.save(update_fields=['collection'])
        Slip.objects.create(slip_id='a', content='甲', chapter=self.chapter)
        for index in range(2, 7):
            chapter = Chapter.objects.create(title=f'第{index}篇', collection=collection)
            Slip.objects.create(slip_id=f'b-{index}', content='乙', chapter=chapter)

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(
                reverse('chapter-api-list'),
                {'collection': collection.pk, 'include_slips': '1'},
            )

        slip_queries = [query for query in queries if 'texts_sliptext' in query['sql'].lower()]
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(slip_queries), 3)

    def test_random_slip_redirects_without_loading_all_ids(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse('random_slip'))

        slip_queries = [query for query in queries if 'texts_sliptext' in query['sql'].lower()]
        self.assertRedirects(response, reverse('slip_detail', args=[self.slip.pk]))
        self.assertLessEqual(len(slip_queries), 2)

    def test_random_slip_redirects_home_when_empty(self):
        Slip.objects.all().delete()

        response = self.client.get(reverse('random_slip'))

        self.assertRedirects(response, reverse('home'))


class PublicApiTests(TestCase):
    def setUp(self):
        self.chapter = Chapter.objects.create(title='API 测试篇')
        self.slip = Slip.objects.create(
            slip_id='API-1',
            content='甲乙',
            chapter=self.chapter,
            order=1,
        )
        self.character = Character.objects.create(glyph='甲', pronunciation='jia')
        SlipChar.objects.create(slip=self.slip, character=self.character, position=1)

    def test_slip_detail_includes_nested_chapter_and_characters(self):
        response = self.client.get(reverse('slip-detail', args=[self.slip.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['chapter']['title'], self.chapter.title)
        self.assertEqual(response.data['characters'][0]['character']['glyph'], '甲')
        self.assertEqual(response.data['characters'][0]['position'], 1)

    def test_anonymous_annotation_submission_is_pending_review(self):
        response = self.client.post(
            reverse('slip-annotations', args=[self.slip.pk]),
            {
                'annotation_type': 'lishi',
                'author': '匿名作者',
                'content': '释读意见',
                'evidence': '证据',
            },
        )

        self.assertEqual(response.status_code, 201)
        annotation = Annotation.objects.get(slip=self.slip)
        self.assertFalse(annotation.is_approved)
        self.assertEqual(annotation.confidence, 1)

    def test_authenticated_model_editor_cannot_write_public_slip_api(self):
        user = get_user_model().objects.create_user(username='editor', password='test')
        user.user_permissions.add(Permission.objects.get(codename='add_sliptext'))
        self.client.force_login(user)

        response = self.client.post(
            reverse('slip-list'),
            {'slip_id': 'API-2', 'content': '新内容'},
        )

        self.assertEqual(response.status_code, 405)

    def test_chapter_comment_submission_is_pending_review(self):
        response = self.client.post(
            reverse('chapter-api-comments', args=[self.chapter.pk]),
            {'author': '匿名作者', 'content': '篇章评论'},
        )

        self.assertEqual(response.status_code, 201)
        comment = ChapterComment.objects.get(chapter=self.chapter)
        self.assertFalse(comment.is_approved)

    def test_chapter_list_can_include_prefetched_slips(self):
        response = self.client.get(
            reverse('chapter-api-list'),
            {'include_slips': '1'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['slips'][0]['slip_id'], self.slip.slip_id)

    def test_chapter_markdown_is_rendered_and_script_tags_are_removed(self):
        self.chapter.description = '# 篇目说明\n\n<script>alert(1)</script>'
        self.chapter.save(update_fields=['description'])

        response = self.client.get(reverse('chapter-api-detail', args=[self.chapter.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertIn('<h1>篇目说明</h1>', response.data['description_html'])
        self.assertNotIn('<script', response.data['description_html'])

    def test_dictionary_search_accepts_simplified_query_for_traditional_character(self):
        traditional_character = Character.objects.create(glyph='漢')

        response = self.client.get(reverse('character-api-list'), {'q': '汉', 'search_type': 'glyph'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['id'], traditional_character.pk)

    def test_collection_comment_submission_is_pending_review(self):
        collection = Collection.objects.create(name='投稿批次')

        response = self.client.post(
            reverse('collection-api-comments', args=[collection.pk]),
            {'author': '匿名作者', 'content': '批次评论'},
        )

        self.assertEqual(response.status_code, 201)
        comment = CollectionComment.objects.get(collection=collection)
        self.assertFalse(comment.is_approved)

    def test_glyph_annotation_submission_is_pending_review(self):
        glyph = Glyph.objects.create(
            character=self.character,
            slip=self.slip,
            position=1,
            image='glyphs/test.png',
        )

        response = self.client.post(
            reverse('glyph-api-annotations', args=[glyph.pk]),
            {
                'annotation_type': 'lishi',
                'author': '匿名作者',
                'content': '字形意见',
            },
        )

        self.assertEqual(response.status_code, 201)
        annotation = GlyphAnnotation.objects.get(glyph=glyph)
        self.assertFalse(annotation.is_approved)

    def test_collection_and_glyph_detail_apis_return_related_data(self):
        collection = Collection.objects.create(name='API 批次')
        self.chapter.collection = collection
        self.chapter.save(update_fields=['collection'])
        glyph = Glyph.objects.create(
            character=self.character,
            slip=self.slip,
            position=1,
            image='glyphs/test.png',
        )

        collection_response = self.client.get(
            reverse('collection-api-detail', args=[collection.pk])
        )
        glyph_response = self.client.get(reverse('glyph-api-detail', args=[glyph.pk]))

        self.assertEqual(collection_response.status_code, 200)
        self.assertEqual(collection_response.data['chapter_count'], 1)
        self.assertEqual(glyph_response.status_code, 200)
        self.assertEqual(glyph_response.data['character']['glyph'], self.character.reading)
        self.assertEqual(glyph_response.data['slip']['slip_id'], self.slip.slip_id)

    def test_submission_requires_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        endpoint = reverse('slip-annotations', args=[self.slip.pk])
        payload = {
            'annotation_type': 'lishi',
            'author': '匿名作者',
            'content': '释读意见',
        }

        missing_token_response = csrf_client.post(endpoint, payload)
        csrf_response = csrf_client.get(reverse('api-csrf'))
        token = csrf_client.cookies['csrftoken'].value
        valid_token_response = csrf_client.post(
            endpoint,
            payload,
            HTTP_X_CSRFTOKEN=token,
        )

        self.assertEqual(missing_token_response.status_code, 403)
        self.assertEqual(csrf_response.status_code, 200)
        self.assertEqual(valid_token_response.status_code, 201)


class BatchImportTests(TestCase):
    def test_markdown_h2_batches_are_attached_to_their_chapters(self):
        script_path = Path(__file__).resolve().parent.parent / 'import.py'
        spec = importlib.util.spec_from_file_location('bamboo_import_script', script_path)
        importer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(importer)

        with TemporaryDirectory() as directory:
            input_path = Path(directory) / 'sample.md'
            input_path.write_text(
                '## 上博简\n'
                '### 曹沫之阵\n'
                '1|甲乙\n'
                '## 郭店简\n'
                '### 老子甲\n'
                '1|丙丁\n',
                encoding='utf-8',
            )

            records = importer.parse_import_file(input_path)
            importer.import_records(records)

        self.assertEqual(Chapter.objects.get(title='曹沫之阵').collection.name, '上博简')
        self.assertEqual(Chapter.objects.get(title='老子甲').collection.name, '郭店简')
        self.assertEqual(Slip.objects.get(chapter__title='曹沫之阵').content, '甲乙')
        self.assertEqual(Slip.objects.get(chapter__title='老子甲').content, '丙丁')

    def test_legacy_chapter_format_without_batch_still_imports(self):
        script_path = Path(__file__).resolve().parent.parent / 'import.py'
        spec = importlib.util.spec_from_file_location('bamboo_import_script', script_path)
        importer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(importer)

        with TemporaryDirectory() as directory:
            input_path = Path(directory) / 'legacy.md'
            input_path.write_text('chapter: 旧格式篇名\n1|甲乙\n', encoding='utf-8')

            importer.import_records(importer.parse_import_file(input_path))

        chapter = Chapter.objects.get(title='旧格式篇名')
        self.assertIsNone(chapter.collection)
        self.assertEqual(Slip.objects.get(chapter=chapter).content, '甲乙')


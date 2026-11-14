import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import test_ui
from northdiary.ui.font_catalog import load_installed_fonts, load_approved_fonts
from northdiary.ui.font_picker import FontPreferences, FontLibraryDialog, FontLicensesDialog


class AuditedFontTests(unittest.TestCase):
    def test_missing_optional_manifest_is_safe(self):
        self.assertEqual(load_installed_fonts(Path('not-an-installed-font-manifest.json')), ())

    def test_only_exact_reviewed_files_load_and_path_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = b'test font file for mocked registration'
            path = root/'Fonts/test.ttf'
            path.parent.mkdir()
            path.write_bytes(data)
            manifest = root/'fonts.json'
            record = {'key':'test','label':'Test','family':'Audited Family','license_name':'Test License',
                      'license_url':'https://example.invalid/license','note':'test',
                      'files':[{'base':'windows','path':'Fonts/test.ttf','sha256':hashlib.sha256(data).hexdigest()}]}
            manifest.write_text(json.dumps({'fonts':[record]}),encoding='utf-8')
            with patch.dict('os.environ', {'WINDIR':str(root)}), \
                 patch('northdiary.ui.font_catalog.QFontDatabase.addApplicationFont',return_value=1) as register, \
                 patch('northdiary.ui.font_catalog.QFontDatabase.applicationFontFamilies',return_value=['Audited Family']):
                loaded = load_installed_fonts(manifest)
                self.assertEqual(len(loaded),1)
                self.assertFalse(loaded[0].bundled)
                self.assertEqual(loaded[0].license_name,'Test License')
                register.assert_called_once()
                register.reset_mock()
                path.write_bytes(b'different font file')
                self.assertEqual(load_installed_fonts(manifest),())
                register.assert_not_called()
                record['files'][0]['path']='../outside.ttf'
                manifest.write_text(json.dumps({'fonts':[record]}),encoding='utf-8')
                self.assertEqual(load_installed_fonts(manifest),())
                register.assert_not_called()

    def test_expanded_library_does_not_automatically_expand_favorites(self):
        preferences = FontPreferences()
        self.assertTrue(any(not font.bundled for font in preferences.catalog))
        self.assertEqual(preferences.selected, {font.family for font in preferences.catalog if font.bundled})
        dialog = FontLibraryDialog(preferences)
        self.addCleanup(dialog.deleteLater)
        dialog.search.setText('小米')
        visible = [dialog.font_list.item(index) for index in range(dialog.font_list.count())
                   if not dialog.font_list.item(index).isHidden()]
        self.assertEqual(len(visible),1)
        self.assertEqual(visible[0].data(256),'MiSans')
        self.assertIn('MiSans',visible[0].toolTip())
        self.assertNotIn('OFL',visible[0].toolTip())

    def test_license_dialog_has_misans_attribution_and_distinct_licenses(self):
        dialog = FontLicensesDialog(load_approved_fonts())
        self.addCleanup(dialog.deleteLater)
        text = dialog.browser.toPlainText()
        self.assertIn('本软件使用了 MiSans 字体',text)
        self.assertIn('MiSans 免费商用许可',text)
        self.assertIn('Bitstream Vera',text)
        self.assertIn('SIL OFL 1.1',text)

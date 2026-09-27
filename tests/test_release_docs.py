import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class ReleaseDocumentationTests(unittest.TestCase):
    def test_six_modules_are_explicit_in_both_user_guides(self):
        fr=(ROOT/'docs'/'USER_GUIDE_FR.md').read_text(encoding='utf-8')
        ar=(ROOT/'docs'/'USER_GUIDE_AR.md').read_text(encoding='utf-8')
        for heading in ('Module Vente','Module Stock','Module Journal','Module Gestion','Module Paramètres','Module Statistiques'):
            self.assertIn(heading,fr)
        for heading in ('وحدة البيع','وحدة المخزون','وحدة السجل','وحدة الإدارة','وحدة الإعدادات','وحدة الإحصائيات'):
            self.assertIn(heading,ar)
    def test_technical_document_covers_required_delivery_topics(self):
        text=(ROOT/'docs'/'TECHNICAL_ARCHITECTURE.md').read_text(encoding='utf-8')
        for term in ('Architecture générale','Dépendances principales','Base de données','Build Windows','Procédure d’installation'):
            self.assertIn(term,text)

if __name__=='__main__':unittest.main()

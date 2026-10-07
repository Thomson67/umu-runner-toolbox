import importlib.util
from pathlib import Path
import tempfile
import unittest

HELPER=Path(__file__).resolve().parents[1]/'toolbox/umu-gameid-manager.py'
if not HELPER.exists(): HELPER=Path(__file__).with_name('ranked.py')
spec=importlib.util.spec_from_file_location('gameid_manager',HELPER)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class MatchingTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  p=Path(self.tmp.name);db=p/'db.csv'
  db.write_text('Dishonored,gog,,umu-1\nDishonored Definitive Edition,steam,,umu-2\nDivinity Original Sin Definitive Edition,steam,,umu-3\nDivinity Original Sin 2 Definitive Edition,steam,,umu-4\nAge of Empires 2 Definitive Edition,steam,,umu-5\nAge of Empires 3 Definitive Edition,steam,,umu-6\nControl,steam,,umu-7\nControl Ultimate Edition,steam,,umu-8\nLife is Strange,steam,,umu-9\nLife is Strange Before the Storm,steam,,umu-10\n')
  self.index=m.CandidateIndex(db,p/'absent')
 def results(self,title):return self.index.candidates(title,20)
 def score(self,title,gid):return next(r[0] for r in self.results(title) if r[2]==gid)
 def test_exact_edition_first(self):
  self.assertEqual(self.results('Dishonored Definitive Edition')[0][2],'umu-2')
  self.assertEqual(self.results('Dishonored Definitive Edition')[0][0],1)
 def test_edition_does_not_match_unrelated_game(self):
  self.assertLess(self.score('Dishonored Definitive Edition','umu-3'),.70)
 def test_unlisted_edition_uses_main_title(self):
  self.assertEqual(self.results('Dishonored Deluxe Edition')[0][2],'umu-1')
  self.assertLess(self.results('Dishonored Deluxe Edition')[0][0],.92)
 def test_different_sequels_not_probable(self):
  self.assertLessEqual(self.score('Divinity Original Sin 2 Definitive Edition','umu-3'),.55)
  self.assertLessEqual(self.score('Age of Empires II Definitive Edition','umu-6'),.55)
 def test_roman_and_arabic_sequel_match(self):
  self.assertEqual(self.results('Age of Empires II Definitive Edition')[0][2],'umu-5')
  self.assertGreater(self.results('Age of Empires II Definitive Edition')[0][0],.92)
 def test_base_title_exact_has_priority(self):
  self.assertEqual(self.results('Control')[0][2],'umu-7')
 def test_subtitle_is_preserved(self):
  core=m.title_parts('Life is Strange Before the Storm')[0]
  self.assertEqual(core,'life is strange before the storm')
  self.assertEqual(self.results('Life is Strange Before the Storm')[0][2],'umu-10')
 def test_cache_and_limits(self):
  self.assertEqual(self.index.candidates('Control',1),self.results('Control')[:1])
  self.assertEqual(m.title_parts('Special Edition')[0],'special edition')

if __name__=='__main__':unittest.main()

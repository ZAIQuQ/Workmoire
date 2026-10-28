"""Release checks are authenticated, bounded, cached and independent of user data."""
import json
import unittest
import urllib.error
from unittest.mock import patch
import app_release as release
import test_documents as support


class ReleaseHttpTests(unittest.TestCase):
    request=support.DocumentHttpTests.request
    setUp=support.DocumentHttpTests.setUp
    tearDown=support.DocumentHttpTests.tearDown

    def test_release_metadata_is_local_until_an_authenticated_check(self):
        with patch.object(release,'fetch_latest') as fetch:
            self.assertEqual(self.request('/api/version?check=1',anonymous=True)[0],401)
            status,body,_=self.request('/api/version');self.assertEqual(status,200)
            data=json.loads(body);self.assertEqual(data['version'],'1.1.0');self.assertNotIn('latest',data)
            self.assertIn('5201',data['notes']);self.assertNotIn('synthetic-reader',body.decode());fetch.assert_not_called()

    def test_update_result_is_cached_and_remote_links_are_not_trusted(self):
        fixture={'tag_name':'v1.2.0','body':'Release notes','html_url':'https://untrusted.example/','prerelease':False,'draft':False}
        with patch.object(release,'_cache',None),patch.object(release,'_cache_until',0),patch.object(release,'fetch_latest',return_value=fixture) as fetch:
            for _ in range(2):
                status,body,_=self.request('/api/version?check=1');self.assertEqual(status,200)
                latest=json.loads(body)['latest'];self.assertEqual(latest['comparison'],'newer');self.assertEqual(latest['url'],'https://github.com/ZAIQuQ/Workmoire/releases/tag/v1.2.0')
            self.assertEqual(fetch.call_count,1)

    def test_unpublished_and_offline_are_not_reported_as_up_to_date(self):
        for error,status in [(urllib.error.HTTPError('https://api.github.com',404,'Not found',{},None),'unpublished'),(TimeoutError(),'unavailable')]:
            with patch.object(release,'_cache',None),patch.object(release,'_cache_until',0),patch.object(release,'fetch_latest',side_effect=error):
                result=release.release_info(True)['latest'];self.assertEqual(result['status'],status);self.assertNotIn('comparison',result)

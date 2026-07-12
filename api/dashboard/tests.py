from django.test import TestCase
from rest_framework.test import APIClient
from media_source.models import MediaSource
from tv_channel.models import Catalog, TvChannel
class DashboardOverviewTests(TestCase):
    def test_empty_overview_contract(self):
        response=APIClient().get('/api/dashboard/overview/')
        self.assertEqual(response.status_code,200);self.assertEqual(response.data['stats']['channels_total'],0);self.assertEqual(response.data['alerts'],[]);self.assertEqual(response.data['on_air'],[])
    def test_counts_enabled_channels_and_stale_sources(self):
        catalog=Catalog.objects.create(name='Test');TvChannel.objects.create(name='Active',catalog=catalog,is_enabled=True);TvChannel.objects.create(name='Disabled',catalog=catalog,is_enabled=False);MediaSource.objects.create(name='Jellyfin',credentials={})
        data=APIClient().get('/api/dashboard/overview/').data
        self.assertEqual(data['stats']['channels_total'],2);self.assertEqual(data['stats']['channels_enabled'],1);self.assertEqual(data['stats']['sources_stale'],1);self.assertEqual(data['alerts'][0]['kind'],'stale_source')

from tests import base
from girder.api.rest import RestException
from girder.constants import ROOT_DIR
from girder.models.model_base import ValidationException

from d1_client.mnclient_2_0 import MemberNodeClient_2_0
from d1_common.types import dataoneTypes
import uuid
import datetime

def setUpModule():

    base.enabledPlugins.append('wholetale')
    base.startServer()


def tearDownModule():

    base.stopServer()


class TestDataONEUpload(base.TestCase):

    def test_generate_public_access_policy(self):
        from server.dataone_package import generate_public_access_policy
        access_policy = generate_public_access_policy()
        assert(access_policy)

    def test_populate_sys_meta(self):
        # Test that populate_sys_meta has the correct default values
        from server.dataone_package import populate_sys_meta

        pid = str(uuid.uuid4())
        format_id = 'text/csv'
        size=256
        md5='12345'
        now = datetime.datetime.now()
        sys_meta = populate_sys_meta(pid, format_id, size, md5, now)
        assert(sys_meta.checksum.algorithm == 'MD5')
        assert(sys_meta.dateUploaded == now)
        assert(sys_meta.dateSysMetadataModified == now)
        assert(sys_meta.formatId == format_id)
        assert(sys_meta.size == size)

    def test_generate_system_metadata(self):
        # Test that the generate_system_metadata is giving the right state

        from server.dataone_package import generate_system_metadata

        pid = str(uuid.uuid4())
        format_id = 'text/csv'
        file_object='12345'

        metadata = generate_system_metadata(pid, format_id, file_object)
        assert(metadata.size == len(file_object))
        assert (metadata.formatId == format_id)
        assert (metadata.checksum.algorithm == 'MD5')

    def test_create_resource_map(self):

        from server.dataone_package import create_resource_map

        resmap_pid = str(uuid.uuid4())
        eml_pid = str(uuid.uuid4())
        file_pids = ['1234', '4321']
        res_map = create_resource_map(resmap_pid, eml_pid, file_pids)
        assert(len(res_map))
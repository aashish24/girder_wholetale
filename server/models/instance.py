#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import time
import ssl

from ..constants import API_VERSION, InstanceStatus
from girder import logger
from girder.constants import AccessType, SortDir
from girder.models.model_base import \
    AccessControlledModel, ValidationException
from girder.plugins.worker import getCeleryApp, getWorkerApiUrl
from girder.api.rest import getApiUrl
from six.moves import urllib

from tornado.httpclient import HTTPRequest, HTTPError, HTTPClient
# FIXME look into removing tornado

TASK_TIMEOUT = 15.0


def _wait_for_server(url, timeout=30, wait_time=0.5):
    """Wait for a server to show up within a newly launched instance."""
    tic = time.time()
    # Fudge factor of IPython notebook bootup.
    time.sleep(0.5)

    http_client = HTTPClient()
    req = HTTPRequest(url)

    while time.time() - tic < timeout:
        try:
            http_client.fetch(req)
        except HTTPError as http_error:
            code = http_error.code
            logger.info(
                'Booting server at [%s], getting HTTP status [%s]',
                url, code)
            time.sleep(wait_time)
        except ssl.SSLError:
            time.sleep(wait_time)
        else:
            break


class Instance(AccessControlledModel):

    def initialize(self):
        self.name = 'instance'
        compoundSearchIndex = (
            ('taleId', SortDir.ASCENDING),
            ('creatorId', SortDir.DESCENDING),
            ('name', SortDir.ASCENDING)
        )
        self.ensureIndices([(compoundSearchIndex, {})])

        self.exposeFields(
            level=AccessType.READ,
            fields={'_id', 'created', 'creatorId', 'name', 'taleId'})
        self.exposeFields(
            level=AccessType.WRITE,
            fields={'containerInfo', 'lastActivity', 'status', 'url'})

    def validate(self, instance):
        if not InstanceStatus.isValid(instance['status']):
            raise ValidationException(
                'Invalid instance status %s.' % instance['status'],
                field='status')
        return instance

    def list(self, user=None, tale=None, limit=0, offset=0,
             sort=None, currentUser=None):
        """
        List a page of jobs for a given user.

        :param user: The user who owns the job.
        :type user: dict or None
        :param limit: The page limit.
        :param offset: The page offset
        :param sort: The sort field.
        :param currentUser: User for access filtering.
        """
        cursor_def = {}
        if user is not None:
            cursor_def['creatorId'] = user['_id']
        if tale is not None:
            cursor_def['taleId'] = tale['_id']
        cursor = self.find(cursor_def, sort=sort)
        for r in self.filterResultsByPermission(
                cursor=cursor, user=currentUser, level=AccessType.READ,
                limit=limit, offset=offset):
            yield r

    def deleteInstance(self, instance, token):
        payload = {
            'instanceId': str(instance['_id']),
            'girder_token': str(token['_id']),
            'apiUrl': getWorkerApiUrl()
        }

        app = getCeleryApp()
        active_queues = list(app.control.inspect().active_queues().keys())

        instanceTask = app.send_task(
            'gwvolman.tasks.shutdown_container', args=[payload],
            queue='manager',
        )
        instanceTask.get(timeout=TASK_TIMEOUT)

        queue = 'celery@{}'.format(instance['containerInfo']['nodeId'])
        if queue in active_queues:
            volumeTask = app.send_task(
                'gwvolman.tasks.remove_volume', args=[payload],
                queue=instance['containerInfo']['nodeId']
            )
            volumeTask.get(timeout=TASK_TIMEOUT)

        # TODO: handle error
        self.remove(instance)

    def createInstance(self, tale, user, token, name=None, save=True):
        if not name:
            name = tale.get('title', '')

        workspaceFolder = self.model('tale', 'wholetale').createWorkspace(tale)

        now = datetime.datetime.utcnow()
        payload = {
            'girder_token': str(token['_id']),
            'apiUrl': getWorkerApiUrl(),
            'taleId': str(tale['_id']),
            'workspaceId': str(workspaceFolder['_id']),
            'api_version': API_VERSION
        }

        volumeTask = getCeleryApp().send_task(
            'gwvolman.tasks.create_volume', args=[payload]
        )
        volume = volumeTask.get(timeout=TASK_TIMEOUT)
        payload.update(volume)

        serviceTask = getCeleryApp().send_task(
            'gwvolman.tasks.launch_container', args=[payload],
            queue='manager'
        )
        service = serviceTask.get(timeout=TASK_TIMEOUT)
        service.update(volume)

        netloc = urllib.parse.urlsplit(getApiUrl()).netloc
        domain = '{}.{}'.format(
            service['name'], netloc.split(':')[0].split('.', 1)[1])
        url = 'http://{}/{}'.format(domain, service.get('urlPath', ''))

        _wait_for_server(url)

        instance = {
            'taleId': tale['_id'],
            'created': now,
            'creatorId': user['_id'],
            'lastActivity': now,
            'containerInfo': service,
            'name': name,
            'status': InstanceStatus.RUNNING,   # be optimistic for now
            'url': url
        }

        self.setUserAccess(instance, user=user, level=AccessType.ADMIN)
        if save:
            instance = self.save(instance)

        return instance

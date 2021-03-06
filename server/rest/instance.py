#!/usr/bin/env python
# -*- coding: utf-8 -*-
from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.docs import addModel
from girder.api.rest import Resource, filtermodel, RestException
from girder.constants import AccessType, SortDir
from girder.utility import path as path_util


instanceModel = {
    'id': 'instance',
    'type': 'object',
    'required': [
        '_accessLevel', '_id', '_modelType', 'containerId',
        'containerPath', 'created', 'folderId', 'frontendId',
        'lastActivity', 'mountPoint', 'status', 'userId',
        'when'
    ],
    'example': {
        '_accessLevel': 2,
        '_id': '587506670791d3000121b68d',
        '_modelType': 'instance',
        'containerInfo': {
            'containerId': '397914f6bf9e4d153dd86',
            'containerPath': 'user/.../login?token=...',
            'host': '172.17.0.1',
            'mountPoint': '/var/lib/docker/volumes/58caa69f9fcbde0001/_data',
            'volumeName': '58ca9fcbde0001df4d26_foo'
        },
        'created': '2017-04-07T17:04:04.777000+00:00',
        'creatorId': '57c099af86ed1d0001733722',
        'lastActivity': '2017-04-07T17:04:04.777000+00:00',
        'name': 'test',
        'status': 0,
        'taleId': '58caa69f9fcbde0001df4d26',
        'url': 'user/hkhHpMloA4Pp/login?token=babf41833c9641a4a92bece48a34e5b7'
    },
    'properties': {
        '_accessLevel': {'type': 'integer', 'format': 'int32'},
        '_id': {'type': 'string'},
        '_modelType': {'type': 'string'},
        'containerInfo': {
            '$ref': '#/definitions/containerInfo'
        },
        'created': {'type': 'string', 'format': 'date'},
        'creatorId': {'type': 'string'},
        'lastActivity': {'type': 'string', 'format': 'date'},
        'name': {'type': 'string'},
        'status': {'type': 'integer', 'format': 'int32',
                   'allowEmptyValue': False,
                   'maximum': 1, 'minimum': 0},
        'taleId': {'type': 'string'},
        'url': {'type': 'string'}
    }
}
addModel('instance', instanceModel, resources='instance')


class Instance(Resource):

    def __init__(self):
        super(Instance, self).__init__()
        self.resourceName = 'instance'

        self.route('GET', (), self.listInstances)
        self.route('POST', (), self.createInstance)
        self.route('GET', (':id',), self.getInstance)
        self.route('DELETE', (':id',), self.deleteInstance)

    @access.user
    @filtermodel(model='instance', plugin='wholetale')
    @autoDescribeRoute(
        Description('Return all the running instances accessible by the user')
        .param('userId', "The ID of the instance's creator.", required=False)
        .param('taleId',  'List all the instanes using this tale.', required=False)
        .param('text', 'Perform a full text search for a tale with a matching '
               'name.', required=False)
        .responseClass('instance', array=True)
        .pagingParams(defaultSort='created', defaultSortDir=SortDir.DESCENDING)
    )
    def listInstances(self, userId, taleId, text, limit, offset, sort, params):
        # TODO: text search is ignored
        currentUser = self.getCurrentUser()
        if taleId:
            tale = self.model('tale', 'wholetale').load(
                taleId, user=currentUser, level=AccessType.READ)
        else:
            tale = None

        if userId:
            user = self.model('user').load(userId, force=True, exc=True)
        else:
            user = None

        # TODO allow to search for instances that belongs to specific user
        return list(self.model('instance', 'wholetale').list(
            user=user, tale=tale, offset=offset, limit=limit,
            sort=sort, currentUser=currentUser))

    @access.user
    @autoDescribeRoute(
        Description('Get an instance by ID.')
        .modelParam('id', model='instance', plugin='wholetale', level=AccessType.READ)
        .responseClass('instance')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the instance.', 403)
    )
    def getInstance(self, instance, params):
        return instance

    @access.user
    @autoDescribeRoute(
        Description('Delete an existing instance.')
        .modelParam('id', model='instance', plugin='wholetale', level=AccessType.WRITE)
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied for the instance.', 403)
    )
    def deleteInstance(self, instance, params):
        self.model('instance', 'wholetale').deleteInstance(
            instance, self.getCurrentToken())

    @access.user
    @autoDescribeRoute(
        Description('Create a new instance')
        .notes('Instantiate a tale.')
        .param('taleId', 'The ID of a tale used to create an instance.',
               required=False)
        .param('imageId', 'The ID of an image used to create a temporary instance.',
               required=False)
        .param('name', 'A user-friendly, short name of the tale.',
               required=False)
        .responseClass('instance')
        .errorResponse('Read access was denied for the tale.', 403)
    )
    def createInstance(self, taleId, imageId, name, params):
        if taleId is None and imageId is None:
            raise RestException(
                'You need to provide "imageId" or "taleId".'
            )
        user = self.getCurrentUser()
        token = self.getCurrentToken()

        taleModel = self.model('tale', 'wholetale')
        if taleId:
            tale = taleModel.load(
                taleId, user=user, level=AccessType.READ)
        elif imageId:
            image = self.model('image', 'wholetale').load(
                imageId, user=user, level=AccessType.READ)
            userDataFolder = path_util.lookUpPath(
                '/user/%s/Data' % user['login'], user)
            folder = userDataFolder['document']
            data = [{'type': 'folder', 'id': folder['_id']}]
            try:
                # Check if it already exists
                tale = next(taleModel.list(user=None, data=data, image=image,
                                           currentUser=user))
            except StopIteration:
                title = 'Testing %s' % image['fullName']
                tale = taleModel.createTale(
                    image, data, creator=user, save=True,
                    title=title, description=None, public=False)

        instanceModel = self.model('instance', 'wholetale')
        return instanceModel.createInstance(tale, user, token, name=name,
                                            save=True)

from pypcae.enums import *
from pypcae.comp import *
from pypcae.stru import StruModel

clc()
a, b, c = 5.4, 0.25,0.5
ah, bh = 2.0, 0.2

nbox = [
    Node(0, 0, 0).id,
    Node(a, 0, 0).id,
    Node(a, b, 0).id,
    Node(0, b, 0).id,
    Node(0, 0, c).id,
    Node(a, 0, c).id,
    Node(a, b, c).id,
    Node(0, b, c).id,
]

nhole = [
    Node(a/2-ah/2, 0, c/2-bh/2).id,
    Node(a/2+ah/2, 0, c/2-bh/2).id,
    Node(a/2+ah/2, 0, c/2+bh/2).id,
    Node(a/2-ah/2, 0, c/2+bh/2).id,
    Node(a/2-ah/2, b, c/2-bh/2).id,
    Node(a/2+ah/2, b, c/2-bh/2).id,
    Node(a/2+ah/2, b, c/2+bh/2).id,
    Node(a/2-ah/2, b, c/2+bh/2).id,
]

wbox = [
    Line(nbox[0], nbox[1]).id,
    Line(nbox[1], nbox[2]).id,
    Line(nbox[2], nbox[3]).id,
    Line(nbox[3], nbox[0]).id,

    Line(nbox[4], nbox[5]).id,
    Line(nbox[5], nbox[6]).id,
    Line(nbox[6], nbox[7]).id,
    Line(nbox[7], nbox[4]).id,

    Line(nbox[1], nbox[5]).id,
    Line(nbox[2], nbox[6]).id,
    Line(nbox[3], nbox[7]).id,
    Line(nbox[0], nbox[4]).id
]

whole = [
    Line(nhole[0], nhole[1]).id,
    Line(nhole[1], nhole[2]).id,
    Line(nhole[2], nhole[3]).id,
    Line(nhole[3], nhole[0]).id,

    Line(nhole[4], nhole[5]).id,
    Line(nhole[5], nhole[6]).id,
    Line(nhole[6], nhole[7]).id,
    Line(nhole[7], nhole[4]).id,

    Line(nhole[1], nhole[5]).id,
    Line(nhole[2], nhole[6]).id,
    Line(nhole[3], nhole[7]).id,
    Line(nhole[0], nhole[4]).id
]

sbottom = Surf([wbox[0], wbox[1], wbox[2], wbox[3]]).id
stop = Surf([wbox[4], wbox[5], wbox[6], wbox[7]]).id
s1 = Surf([wbox[0], wbox[8], wbox[4], wbox[11]], inners=[[whole[0], whole[1], whole[2], whole[3]]]).id
s2 = Surf([wbox[1], wbox[9], wbox[5], wbox[8]]).id
s3 = Surf([wbox[2], wbox[10], wbox[6], wbox[9]], inners=[[whole[4], whole[5], whole[6], whole[7]]]).id
s4 = Surf([wbox[3], wbox[11], wbox[7], wbox[10]]).id
shole1 = Surf([whole[0], whole[8], whole[4], whole[11]]).id
shole2 = Surf([whole[1], whole[9], whole[5], whole[8]]).id
shole3 = Surf([whole[2], whole[10], whole[6], whole[9]]).id
shole4 = Surf([whole[3], whole[11], whole[7], whole[10]]).id

Solid([sbottom, stop, s1, s2, s3, s4, shole1, shole2, shole3, shole4])

StruModel.toViewer()

# The old constituencies nobody keeps around

A few days ago I stumbled onto boundaries.in, which has India's pre-2008 assembly maps,
and it reminded me that I've been sitting on a pile of old shapefiles for years. Somewhere
in the `elections/geo/reference` folder on my laptop - the kind of folder you copy from
machine to machine and never open - there was a full set of pre-delimitation constituency
maps. I went looking. They were there. And they were a mess.

For the uninitiated: in 2008 India redrew almost all its electoral boundaries. The
delimitation exercise kept the *number* of seats per state fixed, but moved the lines. So
a constituency called "Bangalore South" in 2004 and one called "Bangalore South" in 2009
are not the same shape on the ground. This matters more than people assume. If you want to
map the 2004 Lok Sabha result, or any state election before 2008, and you drape it over
today's constituencies, you get a map that is confidently wrong. The current boundaries are
everywhere - ECI, various GitHub repos, half a dozen data journalism projects. The old ones
have quietly disappeared.

What I had was two sets. The Lok Sabha set (543 constituencies, which is the giveaway - 543
is the old number) was clean. Proper WGS84, latitude and longitude where you'd expect them.
The assembly set was another story: no `.prj` file, and every state crammed into a small
local grid where Karnataka and Maharashtra had almost the same coordinates, which is
impossible for a real map. Some unknown projection with no label.

The trick I used to fix it was almost embarrassingly simple. I had the Lok Sabha maps in
correct coordinates, and both sets cover the same states - a state's outline is a state's
outline whether you build it up from assembly seats or parliamentary seats. So for each
state I stretched its assembly bounding box to sit exactly on top of its parliamentary
one. It got the map into honest latitude-longitude, roughly. I was fairly pleased with
myself. Hold that thought.

## Then I went looking for the post-2008 ones too

Having done the old maps, the obvious next move was to add the current ones and put both
in the same place, in the same format. I had the post-2008 shapefiles somewhere too. This
is where the project got more interesting than I expected.

First surprise: one of the files I'd earmarked as "post-2008 assembly", a clean WGS84
national file called AC_All_Final, turned out to be the pre-2008 set. I only caught it
because I checked an internal ID column - INDIAASSEM - against the old per-state files, and
all 224 Karnataka constituencies matched exactly. So this was the same pre-delimitation
data, except somebody had already georeferenced it properly. Which meant the careful
bounding-box hack I was so pleased with was redundant - a better version was sitting on my
own disk the whole time. I threw out the approximation and used the good one. The lesson,
as usual, is to look through all your files before writing clever code.

Second surprise: there was no single clean post-2008 assembly file. The one national
candidate had 4,182 records where there should be about 4,120, and the extras weren't
random. Some constituencies were stored as several polygon rows each - islands, enclaves,
a seat split by a river - which inflated the count. Once I dissolved the polygons back
together by constituency number, 27 of 30 states matched the official Election Commission
counts on the nose. The remaining three - Gujarat, Madhya Pradesh, Sikkim - were genuinely
short, and for those I pulled from a different per-state set I had. This is the unglamorous
reality of "just combine your data": you reconcile two sources against a third ground truth
and stitch the good parts together.

The Assam thing is worth a note because it's a trap. Assam, along with Jammu & Kashmir and
a few northeastern states, was left out of the 2008 delimitation entirely - so for those
states the post-2008 boundaries were the same as the pre-2008 ones. And then Assam got
re-delimited in 2023, and J&K in 2022, and I don't have shapefiles for either. So the
honest position is that my post-2008 layer holds the boundaries valid for roughly 2009
through the early 2020s, and the very latest Assam and J&K maps aren't in it. I've said
exactly that in the README rather than let someone assume the Assam map is current. Getting
the data is only half the job - knowing precisely what vintage it is, and admitting where
it's stale, is the other half.

The repo now has four layers - assembly and parliamentary, pre and post - plus a
constituency-to-Lok-Sabha lookup table for each era, all in WGS84 with the same columns.
The whole thing rebuilds from one Python script using pyshp, no GDAL required. It's on
GitHub. If you ever need to map an Indian election properly, old or recent, this is the
layer you were missing.

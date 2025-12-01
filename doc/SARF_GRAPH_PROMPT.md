I want to add an evaluative visual aid in the `Learn` tab in the personal app
that gives the user an aesthetic sense of how the four main SARF variables
change over time in events on the timeline. That is the main goal of the app,
anyway, to collect data and then help people look back at a visual to see how
their own reactivity and anxiety levels overlap with the symptoms they or
another person is having. It should have it's own button with a graph icon in
the right toolbar, and QAction in the main menu, alongside the add data point
button timeline button, settings buttons.

It would be great if it could fit into the unexpanded QmlDrawer, but I suspect
it would need to expand like the timeline does to give any level of detail. I
would love for it to be a graph where each variable has a different color. But I
am open to ideas on how best to accomplish the goal visually. It could also be
more than one visual in side that Qml View. The code would need to be in Qml
with the logic / data later in python just like all the other models and views
in this app.

The value space of the SAR is just qualitative shifts "up", "down", "same". The
value space of R is RelationshipKind, which doesn't really go up and down but
does indicate a sort of "down"-like shift. If a clinician were drawing it on
paper, they would use their subjective impression of the nature of the events as
reported by the client to draw a graph for each. That impression would have to
do with how they "felt" each line would go up and down in realtion to each
other. The goal is to see very low-resolution, gut-feel correlations in time
across the variables, as the basic clinical hypothesis of Bowen theory that S is
modulated by R via A, and F is the clinical independent variable. This visual
tool will not be a precise scientific instrument, but offer a more-or-less
aesthetic of the simple relationship between these variables.

I am open to both rules-based visuals and AI-based visuals. I already have the
infrastructure to use llm's in the btcopilot backend. The "more-or-less" and
subjective nature of this feature could lend itself to AI graph generation
within a specified graph-appropriate data format. We could also give a narrative
explanation / interpretation of the graph that would be very cool. But I am only
brainstorming right now and don't want to restrict your ideas.

For this task, let's focus first on refining a plan in
familydiagram/doc/SARF_GRAPH.md. This is going to take some thinking and some
back and forth between you and me so lets focus on iterating getting that
document right first and then we can implement that plan. Interview me along the
way to refine you runderstanding of this feature. It may end up simple, but I
think the user story is not totally self-evident right off the bat.
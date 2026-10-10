"""Build outdoor break plans from local activity templates."""

from backend.schemas import ActivityResponse, GenerateRequest

DURATION_NOTES = {
    "Walking": {
        5: "Stay on your own block and keep the loop very short.",
        10: "Walk a familiar sidewalk loop you can finish in about ten minutes.",
        15: "Head toward the nearest trees or park edge, then turn back with time to spare.",
        30: "Take a slower loop on nearby streets or a local greenway, and turn around halfway.",
    },
    "Gardening": {
        5: "Work for about five minutes on a single pot or a handful of weeds.",
        10: "Give yourself ten minutes for one container, one plant, or one small corner.",
        15: "Use the fifteen minutes to water and tidy one bed, then stop even if more remains.",
        30: "Spend the half hour on one garden area, and leave the rest for another day.",
    },
    "Birdwatching": {
        5: "Stay in one spot for five minutes, near a tree, hedge, or garden edge.",
        10: "Watch from one place, or drift to a second nearby perch if the birds move on.",
        15: "Visit two or three close spots, such as a tree, a hedge, and an open patch of sky.",
        30: "Walk a short nearby loop and stop where branches, water, or shrubs offer cover.",
    },
    "Nature Exploration": {
        5: "Study one tree, stone, or garden bed you can reach in a few steps.",
        10: "Explore a courtyard, yard, or planted sidewalk edge for about ten minutes.",
        15: "Wander to the nearest green patch and spend the time looking closely.",
        30: "Follow the closest path, creek edge, or park trail, and turn back at fifteen minutes.",
    },
}

PLANS = {
    ("Walking", "Gentle"): {
        "title": "{minutes}-Minute Gentle Neighborhood Walk",
        "description": (
            "A calm {minutes}-minute walk for when you want fresh air without pushing "
            "your pace. Leave the screen inside, move easily, and come back clearer."
        ),
        "steps": [
            "Leave your screen inside, step outside, and take one easy breath before you start.",
            "{duration_note}",
            "Walk slowly enough to notice the air, the light, and one living thing.",
            "Loop back to your door while the break still feels unhurried.",
        ],
        "tip": "Let your eyes rest on trees or sky instead of looking down the whole time.",
    },
    ("Walking", "Moderate"): {
        "title": "{minutes}-Minute Steady Fresh-Air Walk",
        "description": (
            "A {minutes}-minute walk at a comfortable, purposeful pace. You cover a "
            "little more ground while keeping the route close to home."
        ),
        "steps": [
            "Step outside and pick a route you can walk at a steady pace.",
            "{duration_note}",
            "Swing your arms naturally and look up at the sky or tree line as you go.",
            "Slow down for the last minute and finish back where you started.",
        ],
        "tip": "If you get warm, ease the pace rather than cutting the break short.",
    },
    ("Walking", "Adventurous"): {
        "title": "{minutes}-Minute Wander-the-Long-Way Walk",
        "description": (
            "A {minutes}-minute walk along a greener or less familiar nearby route. "
            "Stay on foot, keep a landmark in mind, and turn back in time."
        ),
        "steps": [
            "Choose a nearby street, hill, or park path you do not usually take.",
            "{duration_note}",
            "When the path splits, take the greener option and use a visible landmark to stay oriented.",
            "Turn around halfway through and walk back before the break runs out.",
        ],
        "tip": "Pick a landmark you can see from the start so the wander stays easy to reverse.",
    },
    ("Gardening", "Gentle"): {
        "title": "{minutes}-Minute Gentle Garden Pause",
        "description": (
            "A small {minutes}-minute gardening pause for one plant, pot, or patch. "
            "The point is to get your hands outside, not to finish the whole garden."
        ),
        "steps": [
            "Step outside to one pot, planter, or small patch of soil.",
            "{duration_note}",
            "Water, pull a few weeds, or gently clear fallen leaves with your hands.",
            "Look closely at one leaf or bloom, then leave the rest for later.",
        ],
        "tip": "One pot is enough. Dirty hands are part of the reset.",
    },
    ("Gardening", "Moderate"): {
        "title": "{minutes}-Minute Hands-On Garden Session",
        "description": (
            "A {minutes}-minute gardening session with one clear job, such as weeding "
            "an edge or watering a row. Stop when the time ends."
        ),
        "steps": [
            "Choose one bed edge, row, or container before you begin.",
            "{duration_note}",
            "Weed, water, or deadhead only inside that boundary.",
            "Brush off your hands, look over what you finished, and go back inside.",
        ],
        "tip": "A clear edge, such as one container or one side of a bed, keeps the session from sprawling.",
    },
    ("Gardening", "Adventurous"): {
        "title": "{minutes}-Minute Bold Garden Burst",
        "description": (
            "A {minutes}-minute start on a bigger outdoor job you can pause, such as "
            "mulching, edging, or refreshing a bed. Progress matters more than perfection."
        ),
        "steps": [
            "Pick one unfinished outdoor job that can stop cleanly when time is up.",
            "{duration_note}",
            "Gather what you need, then work steadily on that single area.",
            "Stop at the time limit, even if the bed is not perfect, and put tools away.",
        ],
        "tip": "End while you still want to continue. The next break can pick up the same spot.",
    },
    ("Birdwatching", "Gentle"): {
        "title": "{minutes}-Minute Quiet Bird Pause",
        "description": (
            "A still {minutes}-minute birdwatching break near a tree, hedge, or open "
            "patch of sky. You listen and look without needing to travel."
        ),
        "steps": [
            "Step outside and stand or sit where you can see branches and sky.",
            "{duration_note}",
            "Stay quiet, listen for calls, and watch for small movements in the leaves.",
            "Notice one bird, or simply the absence of one, then head back in.",
        ],
        "tip": "Birds often show up after you have been still for a minute.",
    },
    ("Birdwatching", "Moderate"): {
        "title": "{minutes}-Minute Neighborhood Bird Walk",
        "description": (
            "A slow {minutes}-minute walk between a few nearby spots where birds gather. "
            "Pause, watch, and then move on."
        ),
        "steps": [
            "Start at the closest tree, hedge, or feeder you can reach on foot.",
            "{duration_note}",
            "At each stop, listen first, then scan trunks, shrubs, and the sky.",
            "Keep the pace slow enough that you are not just passing through.",
        ],
        "tip": "Tree edges, hedges, and water usually hold more birds than open pavement.",
    },
    ("Birdwatching", "Adventurous"): {
        "title": "{minutes}-Minute Birdseeking Loop",
        "description": (
            "A {minutes}-minute search along a greener nearby edge, such as a park "
            "border, creek path, or tree-lined street. Explore a little farther, still on foot."
        ),
        "steps": [
            "Head toward the closest greener edge where birds might shelter.",
            "{duration_note}",
            "Stop whenever you hear a call, and watch until the bird moves or the sound fades.",
            "Turn back with enough time to walk home without rushing.",
        ],
        "tip": "Go only as far as you can return from inside the time you chose.",
    },
    ("Nature Exploration", "Gentle"): {
        "title": "{minutes}-Minute Close-Up Nature Look",
        "description": (
            "A {minutes}-minute look at one small outdoor spot. Study a tree, a patch "
            "of ground, or a garden bed instead of trying to cover distance."
        ),
        "steps": [
            "Walk to the nearest tree, plant, or patch of open ground.",
            "{duration_note}",
            "Look for texture, color, insects, or new growth in that one place.",
            "Name three details you would have missed from a screen, then go back inside.",
        ],
        "tip": "Stay with one small spot. Curiosity works better than covering ground.",
    },
    ("Nature Exploration", "Moderate"): {
        "title": "{minutes}-Minute Nearby Nature Wander",
        "description": (
            "A {minutes}-minute wander through the closest nature you can reach on foot. "
            "Notice plants, insects, textures, and sounds as you go."
        ),
        "steps": [
            "Choose a nearby park entrance, trail, or tree-lined street.",
            "{duration_note}",
            "As you walk, pause for anything that moves, blooms, or changes underfoot.",
            "Collect three observations in your mind, then head back.",
        ],
        "tip": "A park entrance or a row of street trees is enough nature for this break.",
    },
    ("Nature Exploration", "Adventurous"): {
        "title": "{minutes}-Minute Wilder Nearby Ramble",
        "description": (
            "A {minutes}-minute ramble toward the wildest nearby green space you can "
            "reach and still return from in time. Let curiosity lead, and turn around halfway."
        ),
        "steps": [
            "Point yourself toward the greenest nearby path, creek, or park you can reach on foot.",
            "{duration_note}",
            "Follow the route that feels a little wilder, while keeping the way back obvious.",
            "Turn around at the halfway point and finish the break on the walk home.",
        ],
        "tip": "If you leave your immediate block, tell someone your route and honor the turnaround time.",
    },
}


def create_activity(request: GenerateRequest) -> ActivityResponse:
    """Return a break plan for the selected duration, activity, and adventure level."""
    plan = PLANS[(request.activity_type, request.difficulty)]
    minutes = request.duration_minutes
    duration_note = DURATION_NOTES[request.activity_type][minutes]
    steps = [
        step.format(minutes=minutes, duration_note=duration_note) for step in plan["steps"]
    ]
    return ActivityResponse(
        title=plan["title"].format(minutes=minutes),
        description=plan["description"].format(minutes=minutes),
        steps=steps,
        duration_minutes=minutes,
        tip=plan["tip"],
    )

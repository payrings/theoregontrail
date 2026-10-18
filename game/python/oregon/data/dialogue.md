# Dialogue records

The 51 monologues the game offers at its seventeen landmarks, three per landmark, each a speaker and a text. This is the replacement dialogue written for this project; it is not the original game's text. It follows the original's plan (who speaks at each landmark, and what about) in new words. The Python and the TypeScript rebuilds each ship an identical copy of this file. The format is the one the games read: a header line `Landmark N (name), slot S`, then `Speaker:` and `Text:`. A speaker is short enough for the line "<speaker> tells you:" to fit on the screen, and a text is at most 240 characters, so that the game's 240-character read never has to be continued.

### Landmark 0 (Independence)

```
Landmark 0 (Independence), slot 0
  Speaker: An outfitter in town
  Text: Bring extra clothing to barter. Native families along the trail will give fresh fish, greens and game for shirts and socks. At the big rivers a local pilot can be worth the price, though he will ask plenty for his help.

Landmark 0 (Independence), slot 1
  Speaker: A newspaper reader
  Text: A paper I read this morning complains that some emigrants leave with no spares at all, not even a wagon axle. Do they think spares turn up by the roadside? Carry a wheel, an axle and a tongue, or trust to luck.

Landmark 0 (Independence), slot 2
  Speaker: A local farmer
  Text: Two oxen, they tell me, are all some folk mean to take west. That team could hardly shift a loaded wagon, and a single sick animal would leave you stranded. Plan on six at the least.
```

### Landmark 1 (the Kansas River crossing)

```
Landmark 1 (the Kansas River crossing), slot 0
  Speaker: A waiting emigrant
  Text: So many wagons are queued for the ferry that we may sit on this bank for days. Grazing is running thin and hardly anyone hauls fodder. All the same, I prefer a long wait to a crossing in some flimsy boat.

Landmark 1 (the Kansas River crossing), slot 1
  Speaker: A family without cash
  Text: No money for the ferry, so our wagon becomes its own boat. We tip it over, daub the seams with tar, and float our belongings across. The oxen must swim. If the sky opens, the river will rise higher than it already is.

Landmark 1 (the Kansas River crossing), slot 2
  Speaker: The ferry operator
  Text: Do not ford where the water stands over the wagon floor, about thirty inches. It floods the box and washes your goods away. You can waterproof the box and float it across, or be wise and pay for a place on my ferry.
```

### Landmark 2 (the Big Blue River crossing)

```
Landmark 2 (the Big Blue River crossing), slot 0
  Speaker: A leader going home
  Text: We have had our fill and are heading home. Flies plague us by day and mosquitoes by night. The weather swings between blistering heat and bogs of mud. And everyone fears an attack, though we have seen no war party.

Landmark 2 (the Big Blue River crossing), slot 1
  Speaker: A homesick woman
  Text: The prairie is handsome, with its blooms and high grass, but it simply goes on forever. I miss having a town close by. I keep wondering when I will next see shops, a church and crowds of people.

Landmark 2 (the Big Blue River crossing), slot 2
  Speaker: A trail driver
  Text: Take it easy on your animals. Keep the team walking, but at a sensible speed. Hurry them and their feet give out, and a cripple among the oxen is worth about as much as a carcass.
```

### Landmark 3 (Fort Kearney)

```
Landmark 3 (Fort Kearney), slot 0
  Speaker: A fort soldier
  Text: Wagon roads from Independence, St. Joseph and Council Bluffs meet at Fort Kearney. The U.S. Army put up this new post to guard people travelling to Oregon and California.

Landmark 3 (Fort Kearney), slot 1
  Speaker: A wagon guide
  Text: Between Fort Kearney and Fort Laramie the Platte valley is a ready-made highway. Wagons for Oregon, Utah and California all use it. This may be the gentlest part of the journey, with antelope about and buffalo in plenty.

Landmark 3 (Fort Kearney), slot 2
  Speaker: A Fort Kearney scout
  Text: Game remains plentiful, but it takes more effort to find each year. So many wagons pass that I doubt it will last another few years. People fire at animals for sport, carve off a morsel, and leave the rest lying to spoil.
```

### Landmark 4 (Chimney Rock)

```
Landmark 4 (Chimney Rock), slot 0
  Speaker: A cautious wife
  Text: Awful tales go around of parties that ran short of supplies on the road to Oregon, whole families starving. I mean to check our stores often, since we may need longer than we expect. Prepare for the worst, that is my rule.

Landmark 4 (Chimney Rock), slot 1
  Speaker: A young diarist
  Text: By moonlight Chimney Rock is a grand sight. Natives brought fish to our wagon to swap for clothes, and we took quite a few. They plainly understand bargaining, and wanted shirts and stockings above all.

Landmark 4 (Chimney Rock), slot 2
  Speaker: A traveler
  Text: Around noon yesterday Chimney Rock came into view, standing up from the plain like a great tower in a far-off town. We could not look away. It never left our view across twenty miles of prairie until we camped beside it.
```

### Landmark 5 (Fort Laramie)

```
Landmark 5 (Fort Laramie), slot 0
  Speaker: A Sioux warrior
  Text: The Pawnee have always been enemies of my people, and I would not spare one I met. Yet I have never harmed a settler. All I ask is to be left in peace, and for you to keep away from our buffalo.

Landmark 5 (Fort Laramie), slot 1
  Speaker: A grieving woman
  Text: A warning, stranger: do not dig for water. Take it from the river, salty though the Platte is, because that beats the cholera. My husband was buried a week ago. If you have a minute, I could use a hand with this harness.

Landmark 5 (Fort Laramie), slot 2
  Speaker: A mountain man
  Text: Newcomers bound for the Rockies have no idea how to stay alive there. Nights up there freeze, summer or not. Plenty of people who set off over the mountains late in the year were trapped by snow and perished.
```

### Landmark 6 (Independence Rock)

```
Landmark 6 (Independence Rock), slot 0
  Speaker: A young boy
  Text: My name is cut high on Independence Rock, close to the top. Hundreds of others are there too! The earliest were cut by trappers and explorers, men like Fremont, Bonneville and De Smet.

Landmark 6 (Independence Rock), slot 1
  Speaker: A homesick mother
  Text: Not a scrap of butter, cheese or fruit since we left Laramie! I would sooner have a stocked pantry at home than see my name on that boulder. Still, it is better to look at than the graves we keep passing.

Landmark 6 (Independence Rock), slot 2
  Speaker: A trail guide
  Text: Farewell to the Platte, the dunes and the pale buffalo skulls! From here we climb along the Sweetwater to South Pass, where the Continental Divide is crossed. Then it is a sharp drop into the valley of the Green River.
```

### Landmark 7 (South Pass)

```
Landmark 7 (South Pass), slot 0
  Speaker: A Mormon traveler
  Text: I am travelling with my family and forty others to the Great Salt Lake basin, where we hope to worship freely. We were hounded in the East. In Utah we mean to raise a new town and make the desert bloom.

Landmark 7 (South Pass), slot 1
  Speaker: An Arapaho man
  Text: Years ago a few wagons rolled across our country. Now the road is thick with them, and their herds have stripped the grass. Are there any white men left in the East? Some of us speak of leaving.

Landmark 7 (South Pass), slot 2
  Speaker: A young girl
  Text: We are camped while my father recovers from his illness. We drove ourselves too hard, and it cost us our health. Once he is on his feet again, we will move along more slowly.
```

### Landmark 8 (Fort Bridger)

```
Landmark 8 (Fort Bridger), slot 0
  Speaker: A weary widow
  Text: My little one was lost in a swollen stream before Laramie, and typhoid took my husband near Independence Rock. Now five children are all I have, and I drive alone. My oldest is only eleven, and he is growing up too fast.

Landmark 8 (Fort Bridger), slot 1
  Speaker: A trader
  Text: Jim Bridger put up this post. He trapped in the mountains before he set up a smithy and a modest store to serve the emigrants. With his partner Vasquez he deals heavily in horses.

Landmark 8 (Fort Bridger), slot 2
  Speaker: A grumbling wife
  Text: We ought to have used the Sublette Cutoff! This place was hardly worth the detour. Prices are shocking, and the food is rubbish. There are people here who would take your coat and charge you for the privilege.
```

### Landmark 9 (the Green River crossing)

```
Landmark 9 (the Green River crossing), slot 0
  Speaker: A Shoshone man
  Text: At first the wagons did not trouble us. We swapped fish and game with the passing travelers and assisted them across the rivers. But now they are too numerous, and our horses have too little land to graze.

Landmark 9 (the Green River crossing), slot 1
  Speaker: A frugal driver
  Text: Five dollars just to cross the Green by ferry? Those men will pocket a small fortune by breakfast. We shall go downstream and look for a shallow place to ford, and hold on to the few coins we have left.

Landmark 9 (the Green River crossing), slot 2
  Speaker: A young boy
  Text: Back in Independence we bought too little food. Since Laramie we have lived on scraps, and our health shows it. My sister is ill with mountain fever, so for now we are camped here.
```

### Landmark 10 (Soda Springs)

```
Landmark 10 (Soda Springs), slot 0
  Speaker: An eager traveler
  Text: Folks claim you can shave days off the trip by taking the cutoffs, every one of them. Why not take them all? A little danger seems a fair price for saving time and supplies.

Landmark 10 (Soda Springs), slot 1
  Speaker: A tired young woman
  Text: How pretty the Soda Springs are, spurting up again and again on a schedule! It was lovely to rest instead of bouncing around in a wagon from dawn to dusk. In Oregon I shall have a soft bed, and no more nights in a wagon, ever.

Landmark 10 (Soda Springs), slot 2
  Speaker: A young boy
  Text: I am the one who finds firewood every day. It can be hard to gather enough, so I keep a spare supply stashed in a crate beneath the wagon. Out on the plains I collected dry buffalo dung to burn when no wood could be found.
```

### Landmark 11 (Fort Hall)

```
Landmark 11 (Fort Hall), slot 0
  Speaker: A friend going west
  Text: Old friend, our roads part here. I head for California and a fearsome desert. You face the Snake River, and I hear it is a hard one. Write to us the day you arrive in Oregon!

Landmark 11 (Fort Hall), slot 1
  Speaker: A wistful wife
  Text: I hear there are bighorn sheep around here, and water, but almost no firewood. Fort Hall comes as a relief. It saddens me, though, to part from our cousin and everyone else turning for California.

Landmark 11 (Fort Hall), slot 2
  Speaker: A fellow traveler
  Text: Fort Hall is bustling! The broad grassy flats are just right for our worn-out animals. I mean to mend the leaks in our wagon, while my wife longs to scrub all our linen in one of these clean streams.
```

### Landmark 12 (the Snake River crossing)

```
Landmark 12 (the Snake River crossing), slot 0
  Speaker: A frantic wife
  Text: The guidebook states it plainly: hire a native guide to take you over the Snake, for it is a dangerous river unless you know it well. Yet my husband swears we can cross alone!

Landmark 12 (the Snake River crossing), slot 1
  Speaker: An overlander
  Text: Far down in the black lava canyons, writhing and turning, runs the Snake. All that water, and so difficult to reach! Many dry miles lie ahead, so fill your water barrels where you cross.

Landmark 12 (the Snake River crossing), slot 2
  Speaker: A river guide
  Text: Look at that raging river: it is the Snake. Her rapids have swallowed many a craft. Her waters run right down to Oregon! We cross her soon, and once more past Fort Boise. Be careful when you do.
```

### Landmark 13 (Fort Boise)

```
Landmark 13 (Fort Boise), slot 0
  Speaker: A mule trader
  Text: That wagon of yours will never make it over the Blue Mountains, friend. Abandon it and carry your things by pack animal. Buy yourself a pair of strong mules. The trail is strewn with wagon wreckage from people who ignored this advice.

Landmark 13 (Fort Boise), slot 1
  Speaker: An angry wife
  Text: Every fort we reach asks more than the one before. It is scandalous, and we are being fleeced! Given another chance, I would load up far more goods in Independence.

Landmark 13 (Fort Boise), slot 2
  Speaker: A hopeful farmer
  Text: At night my body aches from the work, but my mind is full of the fertile fields of the Willamette. There I will raise a handsome farmstead, and I expect to be rich in five years' time.
```

### Landmark 14 (the Blue Mountains)

```
Landmark 14 (the Blue Mountains), slot 0
  Speaker: A tired overlander
  Text: Past the Snake at Fort Boise it has been all mountains and desert. Dust lies deep, as much as six inches, and rolls up in clouds so thick we see no road. Cattle that swam the river then breathed it in choked, bled and died.

Landmark 14 (the Blue Mountains), slot 1
  Speaker: A mother of three
  Text: From Fort Boise we hugged the desert's rim up to the great wall of the Blue Mountains. The slopes were terribly steep. We chained both back wheels and eased down, and made it safely. Poor beasts, with no water or grass for days.

Landmark 14 (the Blue Mountains), slot 2
  Speaker: A cheerful farmer
  Text: What a joy this Grande Ronde valley is after months of hardship! Plenty of water and grass. If this place is so splendid, the Willamette has to be even better, and our farm will be grand.
```

### Landmark 15 (Fort Walla Walla)

```
Landmark 15 (Fort Walla Walla), slot 0
  Speaker: A young mother
  Text: Since we set out I have dreaded the Indians, though we have seen very few. The ones we did meet guided us across streams or sold us produce. Even so, I am afraid, having read the markers on graves and heard of murders in these hills.

Landmark 15 (Fort Walla Walla), slot 1
  Speaker: A young woman
  Text: My cousin Catherine had been one of six children left orphaned at Whitman's Mission. She lived under their roof for three years, up to the killings last November. Snakes, stampedes, falls, brawls, then a massacre: she survived them all.

Landmark 15 (Fort Walla Walla), slot 2
  Speaker: A Cayuse man
  Text: You ask me about the killings at Whitman's mission. Let me ask something: why could the doctor not heal our children? Measles came with the strangers and took many of them. Why did his medicine spare the settlers' little ones and not ours?
```

### Landmark 16 (The Dalles)

```
Landmark 16 (The Dalles), slot 0
  Speaker: A mountain man
  Text: The last stretch to the Willamette Valley, a hundred miles, is the hardest. You either shoot the wild Columbia by raft or haul your wagon across the steep Cascades. Should you choose the river, find a native guide.

Landmark 16 (The Dalles), slot 1
  Speaker: A valley woman
  Text: My cousin Lydia paid some natives to carry her down the Columbia in a canoe holding seventeen people and all their baggage. A gale forced them ashore to wait. Near dark the waves rose over their heads, but they reached the bank unharmed.

Landmark 16 (The Dalles), slot 2
  Speaker: A toll collector
  Text: I am the keeper of the Barlow Road toll, which is money well spent. Before last year there was no choice; everyone had to float down the Columbia. Mr. Barlow's new road lets you drive your own wagon all the way into Oregon City.
```

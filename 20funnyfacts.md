# Your Broken Arm Is Fine: 20 Oregon Trail Curiosities

By Giacomo Paganelli - rift-demote-fence@duck.com

## Myths and design
1. **Nobody dies of dysentery in this game.** The famous line "You have died of dysentery" does not exist in the game. The game says "[name] has dysentery" in one place and "[name] has died" in another, and it never puts the two together. As far as the game is concerned, your party members die of mysterious causes, and the dysentery is just a coincidence.
2. **There's no separate formula for dying.** If someone catches a second disease before they've recovered from the first, they die, and the second disease is never mentioned. The designer chose this to keep the game simple, and it means poor health costs you more lives. Nobody is told which disease finished them off.
3. **The river rules come from the size of a real wagon.** A wagon has about 30 inches of clearance, which is why you can only ford a river up to 2.5 feet deep. The Indian guide first cut the risks by only 50%, but testers kept having accidents anyway and decided he wasn't worth his fee. The developers made him much more reliable cutting the risks by 80%.
4. **There's a secret menu for teachers.** Press Control-A at the title menu and you get a management screen where a teacher can reset the top ten and erase embarrassing gravestones written by naughty kids. Nothing on the menu tells you it's there.
5. **You can shoot a bison, but you can't carry it home.** A bison weighs 1,700 to 2,000 pounds, but the game lets you bring back at most 100 pounds per hunt. The designer wanted to keep the wagon's load believable and make players think twice about wasting meat.
6. **The game only remembers two gravestones.** Ten would have interrupted play too often, so there's one grave per disk side, and a new one replaces the old.

## Odd corners and bugs  
7. **A broken arm does nothing.** The game numbers injuries and illnesses, and the broken arm is number 0, which is also the number for "healthy". So the game thinks the person is fine even with a broken arm!  
8. **Thieves never take your money.** The code does have a branch for stealing cash, but the thing a thief can pick is never the cash item, so it never happens. And if a thief finds nothing to take, the game shows no message at all.
9. **February always has 28 days.** That's true even in 1848, which was a leap year.  
10. **If you have exactly the Barlow Road toll, you can't pay it.** The game checks that you have more than the toll, so a party with exactly enough money for the toll is told nothing and sent back to choose again. A single cent more and the road opens. Why?  
11. **The final screen gets the century wrong after 1899.** It prints the year as "18" followed by a stored number, so 1905 appears as 18105.   
12. **Waiting at a river is completely safe.** Nobody falls ill or dies while the party waits, however long it takes. A researcher once made a party wait 14,272 game years, which is a very patient wagon. When it finally crossed, it was in such bad shape that it died within days.  
13. **The game crashes if the year goes past 2055.** The game stores the year in a single byte, which overflows, and the game stops with "Error 53 at line #50050".  
14. **The game has climate data for Portland, but it's never used.** The code can only reach five climate zones, numbered 0 to 4, so the sixth row, for Portland, is never read. Sorry Portland!  
15. **The first disk side is completely full, but the second has a leftover.** Side 1 has no free space at all. Side 2, however, still holds a developer's test program for the rafting game, which the game never runs.

## Numbers, number, numbers 
16. **Your chance of falling ill each day is between 1% and 10.3%.** This depends on the party's health: 1% when everyone is perfectly well and 10.3% at the worst health the game allows. The lead designer's book states the range was 0% to 40%, but the code does something else. Luckily for the party, it's gentler than the book.  
17. **Several things can happen on the same day.** Each day, the game checks fifteen possible events one after another, and it doesn't stop at the first one that happens. Yes, it can rain, break a wheel and bring a fever on the same Tuesday.  
18. **The whole game comes down to one number between 0 and 65,535.** The game counts quietly while it waits for you to press a key, and that count decides the luck in your game. However, some numbers give the same game as another number, so instead of 65,536 different games there are effectively only 62,883.
19. **Hunting has its own luck.** The hunting scene uses a separate random number generator, seeded from how long you took at earlier key presses. So even with the same starting number, a game with a hunt can't be replayed exactly.  
20. **Even tiny rounding differences change the game.** In our experiment, using ordinary computer arithmetic instead of the original game's arithmetic changed the course of 55% of the games. It also made the game slightly harder: 22.73% of parties reached Oregon, against 22.86% with the original arithmetic. That was with a fixed start and a player who never made decisions, so it says nothing about a typical human game. A rounding error of a few decimal places can be the difference between Oregon and a gravestone.


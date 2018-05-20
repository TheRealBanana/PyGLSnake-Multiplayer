# PyGLSnake-Multiplayer


Got bored again and wondered to myself, "How hard would it be to make this thing multiplayer?". Hopefully its more diffult than creating PyGLSnake was. 

Answer so far as of May 15th, muuuch harder than I anticipated. So, so much harder.... :/

And as of May 20th, we're basically done with the actual game. All that is left now are minor bug fixes and usability improvements.
I honestly thought the network part was going to be the most difficult but it turned out the hardest part was reimagining how the game logic would work with a server and other clients in the mix. I eventually abandoned the idea of each client ticking at its own rate and made the server dictate each update to the clients. If the server stops sending data, the clients wont work anymore. Each client move is first handled by the server before even that same client gets to see their move on-screen. This isn't a great idea and could cause performance issues. However since the game becomes too difficult to play at low enough tickrates (high framerates = fast moving snakes), its not a real issue.

Here's an interesting stat: The original PyGLSnake I wrote came out to 306 lines of python code. This project, at the time of writing, comes out to 1229 lines of python. Thats a 300% increase in the amount of code, just to add multiplayer functionality to a simple game. Quite impressive.

![Screenshot](https://i.imgur.com/aCOYiNn.jpg)

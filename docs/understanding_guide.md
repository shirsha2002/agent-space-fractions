# নিজের ভাষায় project বোঝার গাইড

এখনকার অবস্থা: official DeepSeek দিয়ে আসল Space Fractions তৈরি হয়েছে। তিনটি paid
call হয়েছে—একবার generation, দুইবার model repair। Conservative cost estimate প্রায়
USD 0.215। Agent-এর 56টি test এবং reviewed game-এর 47টি check পাস করেছে।

Model-এর শেষ output-এ একটি ভুল test vector এবং কিছু UI/authorization edge case
ছিল। Codex সেগুলো ছোট documented patch দিয়ে ঠিক করেছে; তিনটি original model
manifest বদলানো হয়নি। তাই “পুরোটাই নিজে লিখেছি” বা “model একবারেই নিখুঁত বানিয়েছে”
বলবে না। `examples/space_fractions/provenance/`-এ আসল output, failing baseline,
operator changes ও final passing result আলাদা আছে। Game খেলতে API key লাগে না।

এই গাইড মুখস্থ বলার জন্য নয়। আগে software চালাও, code দেখো, তারপর নিজের ভাষায় বোঝাও। Codex-এর সাহায্য নেওয়ার কথা repository-তে লেখা আছে। কোন অংশ নিজে বদলেছ, কোন অংশ tool-assisted, আর কোন game runtime DeepSeek তৈরি করেছে—এগুলো আলাদা করে সত্যভাবে বলবে।

## আসলে আমরা কী বানাচ্ছি

দুটি আলাদা product আছে। প্রথমটি `Task1CodeAgent.exe`: এটি architecture ও UML-এর দুটি file পড়ে, DeepSeek-কে দিয়ে code বানায়, file লিখে, check করে এবং সীমিত repair করতে পারে। দ্বিতীয়টি Space Fractions: agent-এর সত্যিকারের API run থেকে তৈরি হওয়া desktop game।

এখনকার offline diagnostic শুধু agent-এর pipeline পরীক্ষা করে। সেটি ইচ্ছা করে প্রথমে ভুল syntax দেয়, তারপর mocked response দিয়ে repair করে। এতে DeepSeek call হয় না, টাকা লাগে না, এবং সেটি Space Fractions নয়। এই পার্থক্য পরিষ্কার রাখবে।

## দুটি input কেন লাগে

`Architecture_Documentation.md`-এ system-এর উদ্দেশ্য, component, persistence, security ও deployment-এর কথা আছে। `Architecture_View.md`-এ actor, class, state আর interaction-এর UML আছে। শুধু একটি নিলে গুরুত্বপূর্ণ requirement বাদ যেতে পারে।

`input_loader.py` দুটি file আলাদা কিনা, readable UTF-8 কিনা, ফাঁকা বা অতিরিক্ত বড় কিনা দেখে। আসল byte-এর SHA-256 রাখে। Hash হলো file-এর পরিচয়: পরে বোঝা যায় ঠিক কোন input ব্যবহার হয়েছিল। Hash encryption নয়, এবং file-এর content লুকায় না।

`requirements.py` কিছু তথ্য JSON-এ সাজায় এবং কোন file-এর কোন line থেকে এসেছে তা রাখে। তবে পুরো original text-ও model-কে দেয়। তাই JSON extractor কোনো কথা বুঝতে না পারলেও original requirement context-এ থাকে। এটিকে complete natural-language understanding বলা যাবে না।

## Generation কীভাবে হয়

`prompts.py` model-কে বলে complete project একটি JSON manifest হিসেবে ফেরত দিতে। Manifest-এ প্রতিটি file-এর relative path ও পুরো content থাকে। শুধু code-এর টুকরা দেখানো বা আগে লেখা game copy করা এই task পূরণ করে না।

`model_client.py` official DeepSeek endpoint-এ নির্দিষ্ট `deepseek-v4-pro` model ব্যবহার করে। অন্য model চুপচাপ বসায় না। JSON mode format পেতে সাহায্য করে; valid JSON পেলেই code সঠিক বা নিরাপদ হয়ে যায় না। তাই এরপর local checks লাগে।

`workspace_tools.py` আগে manifest দেখে, তারপর নতুন run folder-এ file লেখে। `../` দিলে folder-এর বাইরে চলে যাওয়া সম্ভব, তাই traversal, absolute path, drive/UNC path, duplicate filename এবং Windows reserved filename আটকানো হয়। Link/junction দিয়েও বাইরে যাওয়া হতে পারে, তাই reparse-point checks আছে। একই user-এর concurrent filesystem পরিবর্তন সম্পূর্ণ ঠেকানো যায়—এমন দাবি করা হচ্ছে না।

## Check আর repair কেন আলাদা

প্রথমে static check হয়: Python parse করা যায় কিনা, unsupported import বা কিছু বিপজ্জনক operation আছে কিনা। এতে code চালানো লাগে না। এটি সব ক্ষতিকর code ধরতে পারে না।

Live output এরপর `Review required`-এ থামে। Source দেখে review checkbox দিতে হয়; তারপর test চলে। Test ভুল ধরলে model-কে সীমিত error feedback দিয়ে repair চাওয়া হয়। Repair-এর পরে code বদলেছে, তাই আবার review লাগে। Default সর্বোচ্চ দুই repair; budget আগে শেষ হলে সেখানেই থামবে।

Generated tests model নিজেই লেখে। একই model নিজের ভুলের সঙ্গে মিলে যায় এমন test-ও লিখতে পারে। তাই `contracts.py`-এ agent-এর নিজের independent checks আছে: equivalent fraction, একবার score, pause/resume, next question, game over, restart। সব test pass করলেও GUI, admin edit ও persistence হাতে চালিয়ে দেখতে হবে।

## Fraction আর game state

Fraction comparison-এ floating point এড়িয়ে `fractions.Fraction` ব্যবহার করার contract আছে। `1/2` ও `2/4` একই মান। `1/0` বা code-এর মতো text valid answer নয়; answer যাচাই করতে `eval` চালানো হয় না।

`Game` score ও current question ধরে। `playing` অবস্থায় answer দেওয়া যায়, `paused` অবস্থায় যায় না, শেষ হলে `game_over`। একই question দ্বিতীয়বার submit করলে নতুন point দেওয়া যাবে না। `restart()` score, index ও state reset করে। এগুলো state transition ও scoring rule; GUI button কেমন দেখায় তা থেকে আলাদা।

## API খরচের হিসাব

Professor USD 1-এর মধ্যে রাখতে বলেছেন। কোন কোন call এই সীমার মধ্যে পড়ে তা স্পষ্ট নয়, তাই আমরা সব paid assignment call একসঙ্গে ধরে সীমা রাখছি। এটি আমাদের conservative assumption, professor-এর নিশ্চিত ব্যাখ্যা নয়।

Call পাঠানোর আগে ledger আনুমানিক input bound, সর্বোচ্চ output, margin ধরে টাকা reserve করে। Response এলে provider-এর token usage দিয়ে estimate settle করে। Cache-hit input, cache-miss input ও output-এর rate আলাদা। Reasoning token যদি output-এর অংশ হিসেবে report হয়, সেটিকে আবার আলাদা করে যোগ করলে double count হবে।

Timeout হলে response না পেলেও provider হয়তো কাজ করেছে এবং charge হয়েছে। তাই reservation রেখে পরের paid call বন্ধ থাকে। App বন্ধ করে খুললেও ledger থাকে। Ledger delete করে খরচ লুকানো যাবে না। App-এর estimate provider invoice নয়; বাইরের call app নিজে জানতে পারে না।

এখনই শুধু development করার জন্য credit কেনা জরুরি নয়। Offline checks ও executable ঠিক হলে official account-এ exact model access দেখে, প্রয়োজন হলে credit নিয়ে একবার bounded real generation করব। Key chat-এ দেবে না; masked local field ব্যবহার করবে।

## Desktop বনাম cloud-এর দ্বন্দ্ব

Original architecture-এ web, cloud ও microservices আছে। Email-এ generated game desktop হতে বলা হয়েছে। আমরা ছোট modular local implementation বেছে নিয়েছি যাতে demo করা যায় এবং component responsibilities থাকে। কিন্তু professor এই adaptation approve করেছেন—এমন কথা বলা যাবে না।

Local SQLite persistence PostgreSQL replication নয়। Local admin password role OAuth2 নয়। Single-user game চলে মানেই 1,000 concurrent user বা 99.99% uptime প্রমাণ হয় না। যেগুলো করা হয়নি traceability table-এ তা খোলাখুলি লেখা আছে।

## Executable আর নিরাপত্তা

PyInstaller Python runtime ও প্রয়োজনীয় module সঙ্গে bundle করে। তাই target-এ আগে Python install না থাকলেও executable চলার কথা। Developer machine-এ চলা আর clean Windows-এ Python ছাড়া পরীক্ষা—দুটি আলাদা evidence। Clean test না হলে pending বলবে।

Generated tests ও game চালানোর worker-ও agent executable-এর ভেতরের runtime ব্যবহার করে; `python` command target-এর PATH-এ আছে ধরে নেয় না। Generated game-এর নিজের standalone executable বানানো আলাদা developer build step।

Worker আলাদা process, shell command allow করা হয় না, test-এ timeout ও output limit আছে, API key-এর environment দেওয়া হয় না। তবু code বর্তমান user হিসেবেই চলে। এটিকে full security sandbox বলা যাবে না। অপরিচিত code review করো এবং disposable environment ব্যবহার করো।

## Demonstration-এর আগে যা নিজে যাচাই করবে

- Offline run-এর label পড়ে বুঝবে এটি mock। তারপর real run-এর model, input hash, manifest, test result ও actual token usage খুঁজে দেখবে।
- Game-এ একটি সঠিক ও একটি ভুল answer দেবে, score ও explanation দেখবে, pause/resume এবং restart করবে।
- Admin question edit, invalid input rejection এবং বন্ধ করে খুলে persistence দেখবে—যদি genuine generated output-এ এগুলো implement হয়ে থাকে।
- README-এর command চালিয়ে দেখবে এবং source-এর কোন module কী করে তা খুঁজে পাবে।
- Report-এ pending বা deferred লেখা অংশ মুছে সফল বলা যাবে না, যতক্ষণ না তার evidence আছে।
- Submission-এর আগে repository/video link evaluator খুলতে পারেন কিনা দেখবে; draft email এখনও পাঠানো হয়নি।

বোঝানোর জন্য সবচেয়ে দরকারি flow: **দুটি document → original text ও evidence JSON → real DeepSeek request → validated files → source review → independent এবং generated tests → সীমিত repair → সত্যিকারের run evidence**।

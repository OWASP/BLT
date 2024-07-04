import 'package:blt/src/pages/pages_import.dart';

class ChatBotPage extends StatefulWidget {
  const ChatBotPage({super.key});

  @override
  State<ChatBotPage> createState() => _ChatBotPageState();
}

class _ChatBotPageState extends State<ChatBotPage> {
  TextEditingController messageController = TextEditingController();
  List<Message> messages = [];
  bool loading_message = false;

  @override
  Widget build(BuildContext context) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    final Size size = MediaQuery.of(context).size;

    void getResults(String query) async {
      String response = await ChatBotApiClient.getResponse(query);
      if (response.substring(0, 3) == "err:") {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              response.substring(5),
            ),
          ),
        );
        setState(() {
          loading_message = false;
        });
      } else {
        Message resp =
            Message(message: response.substring(5), type: "response");
        setState(() {
          messages.removeLast();
          messages.add(resp);
          loading_message = false;
        });
      }
    }

    void sendMessage(String message) {
      Message msg = Message(message: message, type: "sent");
      Message loadingMsg = Message(message: "loading", type: "loading");
      setState(() {
        messages.add(msg);
        messages.add(loadingMsg);
        messageController.clear();
        loading_message = true;
      });
      getResults(message);
    }

    return Scaffold(
      backgroundColor: isDarkMode
          ? Color.fromRGBO(34, 22, 23, 1)
          : Theme.of(context).canvasColor,
      appBar: AppBar(
        backgroundColor:
            isDarkMode ? Color.fromRGBO(58, 21, 31, 1) : Color(0xFFDC4654),
        leading: IconButton(
          icon: Icon(
            Icons.arrow_back_ios_new_rounded,
            color: Colors.white,
          ),
          onPressed: () {
            Navigator.of(context).pop();
          },
        ),
        centerTitle: true,
        title: SizedBox(
          width: size.width * 0.3,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              CircleAvatar(
                backgroundImage: AssetImage("assets/app_icon.png"),
              ),
              SizedBox(width: 10),
              Text(
                "BLT Bot",
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 20,
                ),
              ),
            ],
          ),
        ),
      ),
      body: Column(
        children: [
          Expanded(
            child: (messages.isEmpty)
                ? Center(
                    child: Text(
                      'Have a query ? Ask it to BLT Bot !',
                      style: TextStyle(
                        fontSize: 16,
                      ),
                    ),
                  )
                : ConversationBLTBOt(
                    messages: messages.reversed.toList(),
                  ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 2),
            child: Container(
              height: size.height * 0.075,
              width: size.width * 0.97,
              decoration: BoxDecoration(
                  color: Color.fromARGB(255, 247, 246, 246),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: Color(0xFFDC4654),
                  ),
                  boxShadow: [
                    BoxShadow(
                      offset: Offset(0, 0),
                      color: isDarkMode
                          ? Colors.grey.withOpacity(0.3)
                          : Color.fromARGB(255, 213, 212, 212),
                      blurRadius: 10,
                      spreadRadius: 1.2,
                    ),
                  ]),
              child: Padding(
                padding: const EdgeInsets.fromLTRB(15, 8, 8, 8),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    SizedBox(
                      width: size.width * 0.6,
                      child: TextField(
                        enableSuggestions: true,
                        keyboardType: TextInputType.text,
                        maxLines: null,
                        controller: messageController,
                        decoration: const InputDecoration(
                          contentPadding: EdgeInsets.only(left: 8),
                          border: InputBorder.none,
                          iconColor: Colors.grey,
                          hintText: 'Enter your message',
                          hintStyle: TextStyle(
                            fontSize: 18,
                            color: Colors.grey,
                          ),
                        ),
                        style: TextStyle(
                          fontSize: 18,
                          color: Colors.grey[600],
                        ),
                      ),
                    ),
                    GestureDetector(
                      onTap: () {
                        if (messageController.text == "") {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text("Please enter a message."),
                            ),
                          );
                        } else if (loading_message) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text(
                                  "Please wait for the bot to respond before sending another message."),
                            ),
                          );
                        } else {
                          sendMessage(messageController.text.trim().toString());
                        }
                      },
                      child: Container(
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: isDarkMode
                              ? Color.fromRGBO(126, 33, 58, 1)
                              : Color(0xFFDC4654),
                        ),
                        child: Padding(
                          padding: const EdgeInsets.all(10.0),
                          child: Center(
                            child: const Icon(
                              Icons.send_outlined,
                              color: Color.fromARGB(255, 229, 229, 229),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
          SizedBox(height: 12),
        ],
      ),
    );
  }
}

class ConversationBLTBOt extends StatelessWidget {
  const ConversationBLTBOt({super.key, required this.messages});
  final List<Message> messages;

  @override
  Widget build(BuildContext context) {
    final Size size = MediaQuery.of(context).size;
    return ListView.separated(
      reverse: true,
      padding: const EdgeInsets.all(8),
      itemCount: messages.length,
      separatorBuilder: (context, index) => SizedBox(height: 10),
      itemBuilder: (context, index) {
        if (messages[index].type == "sent") {
          return Align(
            alignment: Alignment.centerRight,
            child: Container(
              decoration: BoxDecoration(
                color: Color.fromARGB(255, 237, 97, 111),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Padding(
                padding: const EdgeInsets.all(10.0),
                child: Text(
                  messages[index].message,
                  style: TextStyle(
                    color: Colors.white,
                  ),
                ),
              ),
            ),
          );
        } else if (messages[index].type == "loading") {
          return Align(
            alignment: Alignment.centerLeft,
            child: SizedBox(
              width: 50,
              height: 50,
              child: Lottie.asset(
                "assets/typing.json",
                repeat: true,
              ),
            ),
          );
        } else {
          return Align(
            alignment: Alignment.centerLeft,
            child: Container(
              constraints: BoxConstraints(
                minWidth: size.width * 0.1,
                maxWidth: size.width * 0.6,
              ),
              decoration: BoxDecoration(
                color: Color.fromRGBO(126, 33, 58, 1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Padding(
                padding: const EdgeInsets.all(10.0),
                child: Text(
                  messages[index].message,
                  style: TextStyle(color: Colors.white),
                ),
              ),
            ),
          );
        }
      },
    );
  }
}

class Message {
  String message;
  String type;
  Message({
    required this.message,
    required this.type,
  });

  Message copyWith({
    String? message,
    String? type,
  }) {
    return Message(
      message: message ?? this.message,
      type: type ?? this.type,
    );
  }
}

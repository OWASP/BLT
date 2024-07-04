import 'package:blt/src/pages/drawer/drawer_imports.dart';

class OWASPDonationWebView extends StatefulWidget {
  const OWASPDonationWebView({super.key, required this.selectedIndex});
  final int selectedIndex;
  @override
  State<OWASPDonationWebView> createState() => _OWASPDonationWebViewState();
}

class _OWASPDonationWebViewState extends State<OWASPDonationWebView> {
  WebViewController? _controller;
  bool loading = true;
  @override
  Widget build(BuildContext context) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
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
        title: Text(
          "Sponsor BLT",
          style: TextStyle(
            color: Colors.white,
            fontSize: 20,
          ),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          await _controller?.reload();
          _updateDonationAmount(widget.selectedIndex);
        },
        child: Stack(
          children: [
            if (loading)
              Center(
                child: CircularProgressIndicator(),
              ),
            WebView(
              initialUrl:
                  'https://owasp.org/donate/?reponame=www-project-bug-logging-tool&title=OWASP+Bug+logging+tool',
              javascriptMode: JavascriptMode.unrestricted,
              onWebViewCreated: (WebViewController webViewController) {
                _controller = webViewController;
              },
              onPageFinished: (String url) {
                setState(() {
                  loading = false;
                });
                print(widget.selectedIndex);
                _updateDonationAmount(widget.selectedIndex);
              },
            ),
          ],
        ),
      ),
    );
  }

  void _updateDonationAmount(int index) {
    String javascript = '''
      function selectDonationAmount(index) {
        const donationAmountRows = document.querySelectorAll('.donation-amount-row');

        donationAmountRows.forEach(row => {
          const amountDivs = row.querySelectorAll('div');
          amountDivs.forEach(div => {
            div.classList.remove('selected');
          });
        });

        if (index < 3) {
          donationAmountRows[0].querySelectorAll('div')[index].classList.add('selected');
        } else {
          const modIndex = index % 3;
          donationAmountRows[1].querySelectorAll('div')[modIndex].classList.add('selected');
        }
      }
      selectDonationAmount($index);
    ''';
    _controller?.runJavascript(javascript);
  }
}

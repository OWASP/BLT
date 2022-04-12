import './components/issue_intro_card.dart';
import 'package:flutter/material.dart';
import '../pages/issue_detail.dart';

import '../services/api.dart';
import '../data/models.dart';

class PaginatedClass extends StatefulWidget {
  const PaginatedClass({Key? key}) : super(key: key);

  @override
  PaginatedClassState createState() => PaginatedClassState();
}

ScrollController _scrollController = new ScrollController();

class PaginatedClassState extends State<PaginatedClass>
    with TickerProviderStateMixin {
  late AnimationController animationController;
  bool _loading = true;
  late Future _getObj;
  late String paginatedUrl;

  static const TextStyle optionStyle =
      TextStyle(fontSize: 30, fontWeight: FontWeight.bold);

  @override
  void initState() {
    paginatedUrl = 'https://www.bugheist.com/api/v1/issues/';
    _loading = false;

    animationController =
        AnimationController(duration: new Duration(seconds: 2), vsync: this);
    animationController.repeat();

    _getObj = ApiBackend().getApiData(paginatedUrl);

    _scrollController.addListener(() async {
      if (_scrollController.position.pixels ==
          _scrollController.position.maxScrollExtent) {
        if (!_loading && mounted) {
          setState(() {
            _loading = true;
          });
        }

        _getObj.then((value) async {
          if (value.next != 'null') {
            DataModel _paginatedData =
                await ApiBackend().getApiData(value.next);
            if (mounted) {
              setState(() {
                for (var i = 0; i < _paginatedData.results.length; i++) {
                  value.results.add(_paginatedData.results[i]);
                }
                value.next = _paginatedData.next;
              });
            }
          } else {}
        });
        await Future.delayed(Duration(seconds: 1));
        if (mounted) {
          setState(() {
            _loading = false;
          });
        }
      }
    });
    super.initState();
  }

  @override
  void dispose() {
    animationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Scaffold(
        body: FutureBuilder(
          future: _getObj,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.done) {
              if (snapshot.hasError) {
                return Center(
                  child: Text(
                    'Something went wrong!',
                    style: TextStyle(fontSize: 18),
                  ),
                );
              } else if (snapshot.hasData) {
                return ListView.builder(
                    itemCount: (snapshot.data! as DataModel).results.length + 1,
                    controller: _scrollController,
                    itemBuilder: (context, index) {
                      if (index == (snapshot.data! as DataModel).results.length)
                        return Center(
                          child: Opacity(
                            opacity: _loading ? 1.0 : 0.0,
                            child: CircularProgressIndicator(
                              valueColor: animationController.drive(
                                ColorTween(
                                  begin: Colors.blueAccent,
                                  end: Colors.red,
                                ),
                              ),
                            ),
                          ),
                        );
                      else
                        return new GestureDetector(
                          onTap: () => {
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (context) => ArticleOnePage(
                                  issue: (snapshot.data! as DataModel)
                                      .results[index],
                                ),
                              ),
                            )
                          },
                          child: IssueCard(
                            description: (snapshot.data! as DataModel)
                                .results[index]
                                .description,
                            imageSrc: (snapshot.data! as DataModel)
                                .results[index]
                                .screenshot,
                          ),
                        );
                    });
              }
            }
            return Center(
              child: CircularProgressIndicator(
                valueColor: animationController.drive(
                  ColorTween(
                    begin: Colors.blueAccent,
                    end: Colors.red,
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}

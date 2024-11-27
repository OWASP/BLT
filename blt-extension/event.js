var m;
var global_url;
function n() {
  for (var a = [["edge", /Edge\/([0-9\._]+)/], ["chrome", /Chrom(?:e|ium)\/([0-9\.]+)(:?\s|$)/], ["firefox", /Firefox\/([0-9\.]+)(?:\s|$)/], ["opera", /Opera\/([0-9\.]+)(?:\s|$)/], ["ie", /Trident\/7\.0.*rv\:([0-9\.]+)\).*Gecko$/], ["ie", /MSIE\s([0-9\.]+);.*Trident\/[4-7].0/], ["ie", /MSIE\s(7\.0)/], ["bb10", /BB10;\sTouch.*Version\/([0-9\.]+)/], ["android", /Android\s([0-9\.]+)/], ["ios", /iPad\;\sCPU\sOS\s([0-9\._]+)/], ["ios", /iPhone\;\sCPU\siPhone\sOS\s([0-9\._]+)/], ["safari", /Safari\/([0-9\._]+)/]], 
  b = 0, g = [], b = 0;b < a.length;b++) {
    var k = b, l;
    l = a[b];
    l = l.concat(l[1].exec(navigator.userAgent));
    a[k] = l;
    a[b][2] && g.push(a[b]);
  }
  for (b = (a = g[0]) && a[3].split(/[._]/).slice(0, 3);b && 3 > b.length;) {
    b.push("0");
  }
  g = {};
  g.name = a && a[0];
  g.version = b && b.join(".");
  g.versionInt = parseInt(g.version);
  return g;
}
;window._gaq = window._gaq || [];
var q = {L:function(a) {
  return a + Math.random();
}, ca:function(a) {
  for (var b = a.length, g, k;0 !== b;) {
    k = Math.floor(Math.random() * b), b -= 1, g = a[b], a[b] = a[k], a[k] = g;
  }
  return a;
}, aa:function(a, b) {
  return Math.floor(Math.random() * (b - a + 1) + a);
}}, s = {extend:function(a, b) {
  function g() {
  }
  g.prototype = b.prototype;
  a.prototype = new g;
  a.prototype.constructor = a;
  a.o = b.prototype;
}}, u = {ba:function(a, b, g) {
  var k = q.L(a);
  a = {};
  a[k] = b;
  chrome.storage.local.set(a, function() {
    g && g(k);
  });
}, Z:function(a, b) {
  chrome.storage.local.get(a, function(g) {
    chrome.storage.local.remove(a, function() {
      b && b(g[a]);
    });
  });
}, T:function() {
  return parseInt(window.navigator.appVersion.match(/Chrome\/(\d+)\./)[1], 10);
}}, v = {c:function(a) {
  return chrome.i18n.getMessage(a);
}};
function Notification(a) {
  this.b = a;
  this.k = null;
}
function w(a) {
  w.o.constructor.apply(this, arguments);
  this.create();
}
s.extend(w, Notification);
w.prototype.create = function() {
  var a = this, b = {type:"progress", title:"OWASP BLT-Extension", message:v.c("screenshot_plugin_uploading_window_capt"), iconUrl:"img/icon256.png", buttons:[{title:v.c("screenshot_plugin_cancel")}], isClickable:!0, progress:0};
  50 <= n().da && (b.requireInteraction = !0);
  chrome.notifications.create(this.b, b, function() {
    a.k = "uploading";
  });
};
w.prototype.update = function(a) {
  var b = this;
  "progress" === a.type && a.progress ? chrome.notifications.update(this.b, {progress:a.progress}, function() {
  }) : "success" === a.type && a.message ? (a = {type:"basic", message:a.message, buttons:[{title:v.c("screenshot_plugin_copy")}, {title:v.c("screenshot_plugin_open")}]}, chrome.notifications.update(this.b, a, function() {
    b.k = "success";
  })) : "failed" === a.type && (a = {type:"basic", message:v.c("screenshot_plugin_upload_failed_retry"), buttons:[{title:v.c("screenshot_plugin_retry")}, {title:v.c("screenshot_plugin_cancel")}]}, chrome.notifications.update(this.b, a, function() {
    b.k = "failed";
  }));
};
function x() {
  function a(a) {
    chrome.notifications.clear(a, function() {
    });
    delete b[a];
  }
  var b = {};
  chrome.notifications.onClicked.addListener(function(a) {
    a = b[a];
    "success" === a.k && z.sendMessage({name:A, id:a.b});
  });
  chrome.notifications.onButtonClicked.addListener(function(a, k) {
    var l = b[a];
    "uploading" === l.k && 0 === k ? z.sendMessage({name:B, id:l.b}) : "success" === l.k ? 0 === k ? z.sendMessage({name:C, id:l.b}) : 1 === k && z.sendMessage({name:A, id:l.b}) : "failed" === l.k && (0 === k ? z.sendMessage({name:D, id:l.b}) : 1 === k && z.sendMessage({name:B, id:l.b}));
  });
  return{R:function(g) {
    a(g);
    b[g] = new w(g);
  }, K:function(a, k) {
    b[a].update(k);
  }, u:a};
}
;var E = {save:function(a, b) {
  a && "undefined" != typeof a && "undefined" != typeof a.img_url && $.ajax({type:"POST", url:"http://www.bugheist.com/v1/", data:JSON.stringify({jsonrpc:"2.0", id:1, method:"save", params:a}), dataType:"json", beforeSend:function(a) {
    a.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
  }, complete:function(a) {
    a.responseJSON && "undefined" != typeof a.responseJSON && "undefined" != typeof a.responseJSON.result ? b(a.responseJSON.result) : b(null);
  }});
}};
if ("function" !== typeof F) {
  var F = function() {
    function a(a, h) {
      var e = a[0], c = a[1], d = a[2], f = a[3], e = g(e, c, d, f, h[0], 7, -680876936), f = g(f, e, c, d, h[1], 12, -389564586), d = g(d, f, e, c, h[2], 17, 606105819), c = g(c, d, f, e, h[3], 22, -1044525330), e = g(e, c, d, f, h[4], 7, -176418897), f = g(f, e, c, d, h[5], 12, 1200080426), d = g(d, f, e, c, h[6], 17, -1473231341), c = g(c, d, f, e, h[7], 22, -45705983), e = g(e, c, d, f, h[8], 7, 1770035416), f = g(f, e, c, d, h[9], 12, -1958414417), d = g(d, f, e, c, h[10], 17, -42063), c = g(c, 
      d, f, e, h[11], 22, -1990404162), e = g(e, c, d, f, h[12], 7, 1804603682), f = g(f, e, c, d, h[13], 12, -40341101), d = g(d, f, e, c, h[14], 17, -1502002290), c = g(c, d, f, e, h[15], 22, 1236535329), e = k(e, c, d, f, h[1], 5, -165796510), f = k(f, e, c, d, h[6], 9, -1069501632), d = k(d, f, e, c, h[11], 14, 643717713), c = k(c, d, f, e, h[0], 20, -373897302), e = k(e, c, d, f, h[5], 5, -701558691), f = k(f, e, c, d, h[10], 9, 38016083), d = k(d, f, e, c, h[15], 14, -660478335), c = k(c, d, 
      f, e, h[4], 20, -405537848), e = k(e, c, d, f, h[9], 5, 568446438), f = k(f, e, c, d, h[14], 9, -1019803690), d = k(d, f, e, c, h[3], 14, -187363961), c = k(c, d, f, e, h[8], 20, 1163531501), e = k(e, c, d, f, h[13], 5, -1444681467), f = k(f, e, c, d, h[2], 9, -51403784), d = k(d, f, e, c, h[7], 14, 1735328473), c = k(c, d, f, e, h[12], 20, -1926607734), e = b(c ^ d ^ f, e, c, h[5], 4, -378558), f = b(e ^ c ^ d, f, e, h[8], 11, -2022574463), d = b(f ^ e ^ c, d, f, h[11], 16, 1839030562), c = 
      b(d ^ f ^ e, c, d, h[14], 23, -35309556), e = b(c ^ d ^ f, e, c, h[1], 4, -1530992060), f = b(e ^ c ^ d, f, e, h[4], 11, 1272893353), d = b(f ^ e ^ c, d, f, h[7], 16, -155497632), c = b(d ^ f ^ e, c, d, h[10], 23, -1094730640), e = b(c ^ d ^ f, e, c, h[13], 4, 681279174), f = b(e ^ c ^ d, f, e, h[0], 11, -358537222), d = b(f ^ e ^ c, d, f, h[3], 16, -722521979), c = b(d ^ f ^ e, c, d, h[6], 23, 76029189), e = b(c ^ d ^ f, e, c, h[9], 4, -640364487), f = b(e ^ c ^ d, f, e, h[12], 11, -421815835), 
      d = b(f ^ e ^ c, d, f, h[15], 16, 530742520), c = b(d ^ f ^ e, c, d, h[2], 23, -995338651), e = l(e, c, d, f, h[0], 6, -198630844), f = l(f, e, c, d, h[7], 10, 1126891415), d = l(d, f, e, c, h[14], 15, -1416354905), c = l(c, d, f, e, h[5], 21, -57434055), e = l(e, c, d, f, h[12], 6, 1700485571), f = l(f, e, c, d, h[3], 10, -1894986606), d = l(d, f, e, c, h[10], 15, -1051523), c = l(c, d, f, e, h[1], 21, -2054922799), e = l(e, c, d, f, h[8], 6, 1873313359), f = l(f, e, c, d, h[15], 10, -30611744), 
      d = l(d, f, e, c, h[6], 15, -1560198380), c = l(c, d, f, e, h[13], 21, 1309151649), e = l(e, c, d, f, h[4], 6, -145523070), f = l(f, e, c, d, h[11], 10, -1120210379), d = l(d, f, e, c, h[2], 15, 718787259), c = l(c, d, f, e, h[9], 21, -343485551);
      a[0] = r(e, a[0]);
      a[1] = r(c, a[1]);
      a[2] = r(d, a[2]);
      a[3] = r(f, a[3]);
    }
    function b(a, b, e, c, d, f) {
      b = r(r(b, a), r(c, f));
      return r(b << d | b >>> 32 - d, e);
    }
    function g(a, h, e, c, d, f, g) {
      return b(h & e | ~h & c, a, h, d, f, g);
    }
    function k(a, h, e, c, d, f, g) {
      return b(h & c | e & ~c, a, h, d, f, g);
    }
    function l(a, h, e, c, d, f, g) {
      return b(e ^ (h | ~c), a, h, d, f, g);
    }
    function t(b) {
      var h = b;
      txt = "";
      var e = h.length;
      b = [1732584193, -271733879, -1732584194, 271733878];
      var c;
      for (c = 64;c <= h.length;c += 64) {
        for (var d = h.substring(c - 64, c), f = [], g = void 0, g = 0;64 > g;g += 4) {
          f[g >> 2] = d.charCodeAt(g) + (d.charCodeAt(g + 1) << 8) + (d.charCodeAt(g + 2) << 16) + (d.charCodeAt(g + 3) << 24);
        }
        a(b, f);
      }
      h = h.substring(c - 64);
      d = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0];
      for (c = 0;c < h.length;c++) {
        d[c >> 2] |= h.charCodeAt(c) << (c % 4 << 3);
      }
      d[c >> 2] |= 128 << (c % 4 << 3);
      if (55 < c) {
        for (a(b, d), c = 0;16 > c;c++) {
          d[c] = 0;
        }
      }
      d[14] = 8 * e;
      a(b, d);
      for (h = 0;h < b.length;h++) {
        e = b[h];
        c = "";
        for (d = 0;4 > d;d++) {
          c += y[e >> 8 * d + 4 & 15] + y[e >> 8 * d & 15];
        }
        b[h] = c;
      }
      return b.join("");
    }
    function r(a, b) {
      return a + b & 4294967295;
    }
    var y = "0123456789abcdef".split("");
    "5d41402abc4b2a76b9719d911017c592" != t("hello") && (r = function(a, b) {
      var e = (a & 65535) + (b & 65535);
      return(a >> 16) + (b >> 16) + (e >> 16) << 16 | e & 65535;
    });
    return t;
  }()
}
;function G(a, b) {
  this.b = a;
  this.n = b;
  this.G = this.j = this.a = this.m = null;
  this.g = {};
  this.g[this.f.r] = $.Callbacks();
  this.g[this.f.p] = $.Callbacks();
}
m = G.prototype;
m.f = {r:"progress_change", p:"complete"};
m.h = {v:"success", s:"failed"};
m.l = function() {
  var a = {X:this.j};
  this.a ? a.error = this.a : a.J = this.G;
  return a;
};
m.attachEvent = function(a, b) {
  "undefined" !== typeof this.g[a] && this.g[a].add(b);
};
m.detachEvent = function(a, b) {
  "undefined" !== typeof this.g[a] && this.g[a].remove(b);
};
function H(a, b) {
  b.lengthComputable && a.g[a.f.r].fire({loaded:b.loaded, total:b.total});
}
;function I(a, b, g) {
  I.o.constructor.call(this, a, b);
  this.q = g;
  this.O = "https://api.imgur.com/3/upload.json";
}
s.extend(I, G);
I.Q = "f705f76c81bce12 b4e63420b1461ce 15852baf7d723e5 3df225a9b03b89a 36e07290900869a 905dd4ad0ebc216".split(" ");
m = I.prototype;
m.upload = function() {
  var a = this;
  this.j = this.h.s;
  this.m = $.ajax({url:a.O, type:"POST", timeout:18E4, data:"image=" + encodeURIComponent(a.n.dataUrl.replace(/^data:image\/(png|jpg);base64,/, "")), xhr:function() {
    var b = new XMLHttpRequest;
    b.upload.onprogress = function(b) {
      H(a, b);
    };
    return b;
  }, beforeSend:function(b) {
    a.t(b);
  }, complete:function(b, g) {
    a.w(b, g);
  }});
};
m.t = function(a) {
  a.setRequestHeader("Authorization", "Client-ID " + (this.q || "f705f76c81bce12"));
};
m.w = function(a, b) {
  this.j = this.h.s;
  try {
    var g = JSON.parse(a.responseText);
    g && g.data && g.data.link ? (this.j = this.h.v, this.G = this.A(g)) : this.a = v.c("screenshot_plugin_image_hosting_incorrect_response");
  } catch (k) {
    this.a = v.c("screenshot_plugin_upload_error_capt") + "\n\n", this.a += v.c("screenshot_plugin_upload_error_detailed_info") + ":\n", this.a += "status = " + (a && a.status ? a.status : "") + "\n", this.a += "textStatus = " + b + "\n", this.a += "e = " + k + "\n", this.a += "responseText = " + (a && a.responseText ? a.responseText : "") + "\n";
  }
  this.g[this.f.p].fire(this.l());
};
m.A = function(a) {
  var b = {};
  a && a.data && (a.data.link && (b.img_url = a.data.link), a.data.width && (b.width = a.data.width), a.data.height && (b.height = a.data.height), a.data.S && (b.delete_hash = a.data.S));
  return b;
};
m.cancel = function() {
  this.m && this.m.abort();
};
m.l = function() {
  var a = I.o.l.apply(this, arguments);
  a.key = this.q.substr(this.q.length - 4);
  return a;
};
function J(a, b, g) {
  J.o.constructor.call(this, a, b, g.I);
  this.q = g.I;
  this.V = g.P;
  this.O = "https://imgur-apiv3.p.mashape.com/3/image";
}
s.extend(J, I);
J.Q = [{I:"2dee61a2a821ed3", P:"6bgqwT1DaouxXTKi0yjXLh84RIUZuaaz"}, {I:"095eb04c751288e", P:"wiA790BrM4mshOWa0tVKevgLVJGzp1pGpXGjsnae0ExrxINhs2"}];
J.prototype.t = function(a) {
  a.setRequestHeader("Authorization", "Client-ID " + this.q);
  a.setRequestHeader("X-Mashape-Key", this.V);
};
function K(a, b) {
  K.o.constructor.call(this, a, b);
  this.C = "5CE3DF4D45AC";
  this.W = "https://www.bugheist.com/upload/{time}/{hash}/";
}
s.extend(K, G);
m = K.prototype;

m.upload = function() {
  var a = this;
  this.j = this.h.s;
  var b = function(a) {
    var b = a.split(",");
    a = b[0].match(/:(.*?);/)[1];
    for (var b = atob(b[1]), g = b.length, k = new Uint8Array(g);g--;) {
      k[g] = b.charCodeAt(g);
    }
    return new Blob([k], {type:a});
  }(a.n.dataUrl), g = new FormData;
  g.append("image", b, "image.png");

  


  
  var tempvartime = Math.floor(Date.now() / 1E3);

  var b = tempvartime, k = F("{key}*{time}".replace("{key}", this.C).replace("{time}", b)), b = this.W.replace("{time}", b).replace("{hash}", k);
  var tempvar = k;
  this.m = $.ajax({processData:!1, contentType:!1, url:b, type:"POST", timeout:18E4, data:g, xhr:function() {
    var b = new XMLHttpRequest;
    b.upload.onprogress = function(b) {
      H(a, b);
    };
    return b;
  }, beforeSend:function(b) {
    a.t(b);
  }, complete:function(b, g) {
    chrome.tabs.create({ url: 'https://www.bugheist.com/report/?hash='+ tempvar + '&time='+ tempvartime +'&url=' + global_url});
    //a.w(b, g);
  }});
};
m.t = function() {
};
m.w = function(a, b) {
  this.j = this.h.s;
  try {
    var g = $.parseXML(a.responseText);
    g && g.getElementsByTagName("url").length ? (this.j = this.h.v, this.G = this.A(g)) : this.a = v.c("screenshot_plugin_image_hosting_incorrect_response");
  } catch (k) {
    this.a = v.c("screenshot_plugin_upload_error_capt") + "\n\n", this.a += v.c("screenshot_plugin_upload_error_detailed_info") + ":\n", this.a += "status = " + (a && a.status ? a.status : "") + "\n", this.a += "textStatus = " + b + "\n", this.a += "e = " + k + "\n", this.a += "responseText = " + (a && a.responseText ? a.responseText : "") + "\n";
  }
  this.g[this.f.p].fire(this.l());
};
m.A = function(a) {
  var b = {};
  a && a.getElementsByTagName("url").length && (a.getElementsByTagName("url")[0].innerHTML && (b.img_url = a.getElementsByTagName("url")[0].innerHTML), a.getElementsByTagName("thumb")[0].innerHTML && (b.thumb_url = a.getElementsByTagName("thumb")[0].innerHTML), b.width = 0, b.height = 0, b.delete_hash = "");
  return b;
};
m.cancel = function() {
  this.m && this.m.abort();
};
m.l = function() {
  var a = K.o.l.apply(this, arguments);
  a.key = this.C.substr(this.C.length - 4);
  return a;
};
function L(a, b) {
  this.b = a;
  this.n = b;
  var g = this;
  this.B = [];
  this.B.push(function() {
    return new K(g.b, g.n);
  });
  this.D = 0;
  this.F = this.H = this.N = this.M = this.d = null;
}
function M(a) {
  a.H = function(b) {
    N(a, b);
  };
  a.d.attachEvent(a.d.f.p, a.H);
  a.F = function(b) {
    z.sendMessage({name:O, id:a.b, progress:Math.round(b.loaded / b.total * 100)});
  };
  a.d.attachEvent(a.d.f.r, a.F);
}
function P(a) {
  a.d.detachEvent(a.d.f.p, a.H);
  a.d.detachEvent(a.d.f.r, a.F);
}
L.prototype.upload = function() {
  this.d = this.B[this.D]();
  M(this);
  Q.e("upload", "hosting", "attempt");
  this.d.upload();
};
function N(a, b) {
  b.X === a.d.h.v ? (a.M = b.J.img_url, a.n.cmdAfterUpload === R ? z.sendMessage({name:S, id:a.b}) : (b.J.dpr = a.n.dpr, Q.e("upload", "prntscr", "attempt"), E.save(b.J, function(b) {
    b && b.success && b.url ? (a.N = b.url, Q.e("upload", "prntscr", "success")) : Q.e("upload", "prntscr", "fail");
    z.sendMessage({name:S, id:a.b});
    Q.e("upload", "prntscr", "finished");
  })), Q.e("upload", "hosting", "success_" + b.key)) : (Q.e("upload", "hosting", "fail_" + b.key), T(a));
  Q.e("upload", "hosting", "finished");
}
function T(a) {
  a.D++;
  a.D < a.B.length ? (P(a), a.d = null, a.upload()) : (z.sendMessage({name:U, id:a.b}), Q.e("upload", "totalfail"));
}
L.prototype.cancel = function() {
  this.d.cancel();
  P(this);
  Q.e("upload", "cancel");
};
function W() {
  this.i = {};
}
W.prototype.upload = function(a, b) {
  this.i[a] = new L(a, b);
  this.i[a].upload();
  z.sendMessage({name:X, id:a});
  Q.e("upload", "attempt");
};
function Y(a, b) {
  var g;
  a.i[b] ? (g = a.i[b], g = g.N || g.M) : g = null;
  return g;
}
;var D = "upload_screenshot", X = "upload_started", O = "upload_progress", S = "upload_success", U = "upload_failed", A = "open_screenshot_link", C = "copy_screenshot_link", B = "cancel_upload", R = "search_google";
var Q = function(a) {
  (function() {
    window._gaq.push(["_setAccount", a]);
    window._gaq.push(["_trackPageview"]);
    var b = document.createElement("script");
    b.type = "text/javascript";
    b.async = !0;
    b.src = "https://ssl.google-analytics.com/ga.js";
    var g = document.getElementsByTagName("script")[0];
    g.parentNode.insertBefore(b, g);
  })();
  return{e:function(a, g, k, l, t) {
    window._gaq.push(["_trackEvent", a, g, k, l, t]);
  }};
}("-------"), z = function() {
  function a(a) {
    a.clipboardData.setData("text/plain", c);
    a.preventDefault();
  }
  function b(a, b, c) {
    if (a && "undefined" !== typeof a && "undefined" !== typeof a.name) {
      switch(a.name) {
        case "load_screenshot":
          a = a.id;
          b = "";
          void 0 !== typeof f[a] && (b = f[a], delete f[a]);
          c(b);
          break;
        case D:
          l(a.id), c();
      }
    }
  }
  function g(a) {
    k(a, function() {
      if (d[a] && d[a].cmdAfterUpload) {
        var b = Y(h, a);
        switch(d[a].cmdAfterUpload) {
          case R:
            chrome.tabs.create({url:"http://www.google.com/searchbyimage?image_url=" + b});
            break;
          case "share_twitter":
            chrome.tabs.create({url:"http://twitter.com/home?source=OWASP_BLT&status=" + b + "%20"});
            break;
          case "share_facebook":
            chrome.tabs.create({url:"https://www.facebook.com/dialog/share?app_id=585941498129307&display=page&href=" + b + "&redirect_uri=" + b});
            break;
          case "share_vk":
            chrome.tabs.create({url:"http://vk.com/share.php?url=" + b});
            break;
          case "share_pinterest":
            chrome.tabs.create({url:"http://pinterest.com/pin/create/button/?url=" + b + "&media=" + b + "/direct"});
        }
        e.u(a);
      } else {
        e.K(a, {type:"success", message:Y(h, a)});
      }
    });
  }
  function k(a, b) {
    chrome.storage.local.remove(a, function() {
      b && b();
    });
  }
  function l(a) {
    chrome.storage.local.get(a, function(b) {
      b = b[a];
      d[a] = b;
      h.upload(a, b);
    });
  }
  function t(a) {
    r(a);
  }
  function r(a) {
    y(a, function(a) {
      var b = q.L("screenshot_");
      f[b] = a;
      chrome.tabs.create({url:chrome.extension.getURL("screenshot.html?id=" + b)}, function(a) {
        if ("function" == typeof chrome.tabs.Y) {
          try {
            chrome.tabs.Y(a.id, 1);
          } catch (b) {
          }
        }
      });
    });
  }
  function y(a, b) {
    var c = u.T();
    1 == window.devicePixelRatio || 38 != c && 39 != c ? chrome.tabs.captureVisibleTab({format:"png"}, function(a) {
        chrome.tabs.query({'active': true, 'windowId': chrome.windows.WINDOW_ID_CURRENT},
   function(tabs){
    global_url =  tabs[0].url;
   }
);
      b(a);
    }) : V(a, b);
  }
  function V(a, b) {
    var c = a.width, d = a.height;
    1 != window.devicePixelRatio && (c = Math.floor(a.width * window.devicePixelRatio), d = Math.floor(a.height * window.devicePixelRatio));
    chrome.tabCapture.capture({video:!0, audio:!1, videoConstraints:{mandatory:{minWidth:c, minHeight:d, maxWidth:c, maxHeight:d}}}, function(a) {
      if (a) {
        var e = document.createElement("video");
        e.onloadedmetadata = function() {
          var f = document.createElement("canvas");
          f.width = c;
          f.height = d;
          var g = f.getContext("2d");
          e.play();
          g.drawImage(e, 0, 0);
          e.pause();
          e.src = "";
          a.stop();
          f = f.toDataURL("image/png");
          b(f);
        };
        e.src = window.URL.createObjectURL(a);
      } else {
        chrome.tabs.captureVisibleTab({format:"png"}, function(a) {
          b(a);
        });
      }
    });
  }
  var h = null, e = null, c = null, d = {}, f = {};
  return{U:function() {
    h = new W;
    e = x();
    chrome.browserAction.onClicked.addListener(t);
    chrome.runtime.onMessage.addListener(b);
    document.addEventListener("copy", a);
    var c = chrome.runtime.getManifest().version;
    "undefined" === typeof localStorage.lightshot_version ? localStorage.ever_updated = "no" : localStorage.lightshot_version != c && (localStorage.ever_updated = "yes");
    localStorage.lightshot_version = c;
  }, sendMessage:function(a) {
    if (a && "undefined" !== typeof a && "undefined" !== typeof a.name) {
      switch(a.name) {
        case X:
          e.R(a.id);
          break;
        case O:
          e.K(a.id, {type:"progress", progress:a.progress});
          break;
        case S:
          g(a.id);
          break;
        case U:
          e.K(a.id, {type:"failed"});
          break;
        case A:
          chrome.tabs.create({url:Y(h, a.id)});
          e.u(a.id);
          break;
        case C:
          c = Y(h, a.id);
          document.execCommand("copy");
          e.u(a.id);
          break;
        case B:
          k(a.id, function() {
            var b = h, c = a.id;
            b.i[c] && (b.i[c].cancel(), delete b.i[c]);
          }), e.u(a.id);
      }
    }
  }};
}();
z.U();


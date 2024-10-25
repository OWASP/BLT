var n;

function aa(a) {
    function b() {
        d || (d = $("<div></div>").css({
            position: "absolute",
            top: -9999,
            left: -9999,
            width: "auto",
            height: "auto",
            padding: 0,
            margin: 0,
            webkitTransform: c.css("webkitTransform"),
            webkitTransformOrigin: c.css("webkitTransformOrigin"),
            resize: "none"
        }).appendTo(document.getElementsByTagName("body")[0]));
        d.css({
            fontSize: c.css("fontSize"),
            fontFamily: c.css("fontFamily"),
            lineHeight: c.css("lineHeight")
        });
        var b = a.value.replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/&/g, "&amp;").replace(/$/, "&nbsp;").replace(/\n/g,
                "&nbsp;<br/>").replace(/\s/g, "&nbsp;"),
            e = b.split("<br/>").length - 1;
        d.html(b);
        c.css({
            width: d.width() + f + "px"
        });
        c.attr("rows", e + 2)
    }
    var c = $(a),
        d = null,
        f = Number.parseInt(c.css("font-size"));
    c.css({
        overflow: "hidden"
    });
    c.keyup(b).keydown(b).keypress(b).change(b).change()
};
window._gaq = window._gaq || [];

function v(a, b) {
    this.x = this.y = 0;
    "undefined" !== typeof a && "undefined" !== typeof b && (this.x = a, this.y = b)
}
v.prototype.isEqual = function(a) {
    return this.x === a.x && this.y === a.y
};

function x(a, b) {
    this.c = this.a = 0;
    "undefined" !== typeof a && "undefined" !== typeof b && (this.c = a, this.a = b)
}
x.prototype.isEqual = function(a) {
    return this.c === a.c && this.a === a.a
};

function Rect(a, b) {
    this.x = this.c = this.y = this.a = 0;
    a && ("undefined" !== typeof a.G && "undefined" !== typeof a.I && "undefined" !== typeof a.H && "undefined" !== typeof a.J ? (this.x = Math.min(a.G, a.H), this.c = Math.abs(a.H - a.G), this.y = Math.min(a.I, a.J), this.a = Math.abs(a.J - a.I)) : "undefined" !== typeof a.x && "undefined" !== typeof a.y && "undefined" !== typeof a.c && "undefined" !== typeof a.a ? (this.x = a.x, this.c = a.c, this.y = a.y, this.a = a.a) : "undefined" !== typeof a.left && "undefined" !== typeof a.top && "undefined" !==
        typeof a.right && "undefined" !== typeof a.bottom ? (this.x = a.left, this.c = a.right - a.left, this.y = a.top, this.a = a.top - a.bottom) : "undefined" !== typeof a.x && "undefined" !== typeof a.y && "undefined" !== typeof b.c && "undefined" !== typeof b.a && (this.x = a.x, this.c = b.c, this.y = a.y, this.a = b.a))
}

function ba(a, b, c) {
    b = null == b ? 1 : b;
    c = null == c ? b : c;
    a.x -= b;
    a.y -= c;
    a.c += 2 * b;
    a.a += 2 * c
}

function E(a, b) {
    return b.x >= a.x && b.x <= a.x + a.c && b.y >= a.y && b.y <= a.y + a.a
}

function ca(a, b) {
    return E(a, da(b)) && E(a, G(b)) && E(a, I(b)) && E(a, J(b))
}

function ea(a, b) {
    var c = a.x,
        d = a.y,
        f = b.x,
        h = b.y,
        e;
    e = c + a.c;
    var g;
    g = d + a.a;
    var t;
    t = f + b.c;
    var k;
    k = h + b.a;
    c < f && (c = f);
    d < h && (d = h);
    e > t && (e = t);
    g > k && (g = k);
    e -= c;
    g -= d;
    return 0 < e && 0 < g ? new Rect({
        x: c,
        y: d,
        c: e,
        a: g
    }) : new Rect
}
Rect.prototype.isEqual = function(a) {
    a = new Rect(a);
    return this.x === a.x && this.y === a.y && this.c === a.c && this.a === a.a
};
Rect.prototype.l = function() {
    return 0 === this.c || 0 === this.a
};

function da(a) {
    return new v(a.x, a.y)
}

function G(a) {
    return new v(a.x + a.c, a.y)
}

function I(a) {
    return new v(a.x, a.y + a.a)
}

function J(a) {
    return new v(a.x + a.c, a.y + a.a)
}
Rect.prototype.size = function() {
    return new x(this.c, this.a)
};

function fa(a, b) {
    if (ca(b, a)) {
        var c = b.a / 2,
            d = a.a / 2;
        a.x = b.x + b.c / 2 - a.c / 2;
        a.y = b.y + c - d
    }
}
var K = {
    Aa: function(a, b) {
        return new Rect({
            x: Math.min(a.x, b.x),
            y: Math.min(a.y, b.y),
            c: Math.abs(a.x - b.x),
            a: Math.abs(a.y - b.y)
        })
    },
    t: function(a, b) {
        return new Rect({
            G: a.x - b,
            I: a.y - b,
            H: a.x + b,
            J: a.y + b
        })
    },
    Ua: function(a, b, c) {
        return a.x == b.x ? new Rect({
            G: Math.min(a.x, c.x),
            H: Math.max(a.x, c.x),
            I: Math.min(a.y, b.y),
            J: Math.max(a.y, b.y)
        }) : new Rect({
            G: Math.min(a.x, b.x),
            H: Math.max(a.x, b.x),
            I: Math.min(a.y, c.y),
            J: Math.max(a.y, c.y)
        })
    }
};
var ga = {
        Z: function(a) {
            return a + Math.random()
        },
        kb: function(a) {
            for (var b = a.length, c, d; 0 !== b;) d = Math.floor(Math.random() * b), b -= 1, c = a[b], a[b] = a[d], a[d] = c;
            return a
        },
        jb: function(a, b) {
            return Math.floor(Math.random() * (b - a + 1) + a)
        }
    },
    ha = {
        Na: function(a) {
            var b = window.location.href,
                b = b.substring(b.indexOf("?") + 1); - 1 != b.indexOf("#") && (b = b.split("#")[1]);
            for (var b = b.split("&"), c = 0; c < b.length; c++) {
                var d = b[c].split("=");
                if (1 < d.length && d[0] == a) return d[1]
            }
            return null
        }
    },
    L = {
        aa: function(a) {
            a = /matrix\([^\)]+\)/.exec(window.getComputedStyle(a)["-webkit-transform"]);
            var b = {
                x: 1,
                y: 1
            };
            a && (a = a[0].replace("matrix(", "").replace(")", "").split(", "), b.x = parseFloat(a[0]), b.y = parseFloat(a[3]));
            return b
        },
        ea: function(a) {
            1 != window.devicePixelRatio && (a.style.webkitTransform = "scale(" + 1 / window.devicePixelRatio + ")", a.style.webkitTransformOrigin = "0 0")
        },
        Ga: function(a, b) {
            a.style.webkitTransform = b.style.webkitTransform;
            a.style.webkitTransformOrigin = b.style.webkitTransformOrigin
        },
        Ba: function(a, b, c) {
            a.style.position = "absolute";
            a.style.left = b + "px";
            a.style.top = c + "px"
        }
    },
    N = {
        extend: function(a,
            b) {
            function c() {}
            c.prototype = b.prototype;
            a.prototype = new c;
            a.prototype.constructor = a;
            a.h = b.prototype
        }
    },
    ia = {
        Za: function(a, b, c) {
            var d = ga.Z(a);
            a = {};
            a[d] = b;
            chrome.storage.local.set(a, function() {
                c && c(d)
            })
        },
        hb: function(a, b) {
            chrome.storage.local.get(a, function(c) {
                chrome.storage.local.remove(a, function() {
                    b && b(c[a])
                })
            })
        },
        Pa: function() {
            return parseInt(window.navigator.appVersion.match(/Chrome\/(\d+)\./)[1], 10)
        }
    },
    O = function() {
        var a = [
            [-12, 0],
            [-12, -4],
            [0, 0],
            [-12, 4]
        ];
        return {
            Va: function(a, c, d, f, h, e, g) {
                var t = a.fillStyle,
                    k = a.strokeStyle;
                a.beginPath();
                a.fillStyle = g;
                a.moveTo(c + e, d);
                a.lineTo(c + f - e, d);
                a.quadraticCurveTo(c + f, d, c + f, d + e);
                a.lineTo(c + f, d + h - e);
                a.quadraticCurveTo(c + f, d + h, c + f - e, d + h);
                a.lineTo(c + e, d + h);
                a.quadraticCurveTo(c, d + h, c, d + h - e);
                a.lineTo(c, d + e);
                a.quadraticCurveTo(c, d, c + e, d);
                a.fill();
                a.closePath();
                a.fillStyle = t;
                a.strokeStyle = k
            },
            Ia: function(b, c, d, f, h, e, g) {
                b.strokeStyle = e;
                b.fillStyle = e;
                b.lineWidth = g;
                e = Math.atan2(h - d, f - c);
                var t = g / 2;
                g = [];
                for (p in a) g.push([a[p][0] * t, a[p][1] * t]);
                if (0 == e) e = g;
                else {
                    t = [];
                    for (p in g) {
                        var k =
                            g[p][0],
                            u = g[p][1];
                        t.push([k * Math.cos(e) - u * Math.sin(e), k * Math.sin(e) + u * Math.cos(e)])
                    }
                    e = t
                }
                g = [];
                for (p in e) g.push([e[p][0] + f, e[p][1] + h]);
                b.beginPath();
                b.moveTo(g[0][0], g[0][1]);
                for (p in g) 0 < p && b.lineTo(g[p][0], g[p][1]);
                b.lineTo(g[0][0], g[0][1]);
                b.fill();
                Math.sqrt(Math.pow(f - c, 2) + Math.pow(h - d, 2)) > Math.sqrt(Math.pow(g[0][0] - c, 2) + Math.pow(g[0][1] - d, 2)) && (b.beginPath(), b.moveTo(c, d), b.lineTo(g[0][0], g[0][1]), b.stroke())
            },
            fa: function(a, c, d, f, h) {
                var e = a.lineWidth / 2;
                c = new Rect({
                    x: c,
                    y: d,
                    c: f,
                    a: h
                });
                ba(c, -e, -e);
                a.strokeRect(c.x, c.y, c.c, c.a)
            }
        }
    }();

function ja(a) {
    function b() {
        $(window).off("mouseup", b);
        $(window).off("mousemove", c);
        return !1
    }

    function c(b) {
        L.Ba(a, b.pageX - d, b.pageY - f);
        return !1
    }
    var d = 0,
        f = 0;
    $(a).on("mousedown", function(h) {
        if (h.target === a) {
            var e = $(a);
            $(window).on("mouseup", b);
            e = e.offset();
            d = h.pageX - e.left;
            f = h.pageY - e.top;
            $(window).on("mousemove", c);
            return !1
        }
        return !0
    })
}
var P = {
        d: function(a) {
            return chrome.i18n.getMessage(a)
        }
    },
    ka = function() {
        function a(a) {
            var c = "unknown"; - 1 != a.navigator.appVersion.indexOf("Win") ? c = "windows" : -1 != a.navigator.appVersion.indexOf("Mac") ? c = "macos" : -1 != a.navigator.appVersion.indexOf("X11") ? c = "unix" : -1 != a.navigator.appVersion.indexOf("Linux") && (c = "linux");
            return c
        }
        return {
            gb: a,
            sa: function(b) {
                var c = {
                    id: "ctrl",
                    display: "Ctrl"
                };
                "macos" === a(b) && (c = {
                    id: "meta",
                    display: "\u2318"
                });
                return c
            }
        }
    }();
(function() {
    function a() {
        d(function(a) {
            a && ($("#announce_message").html(f.text), $("#announce").show(), $("#announce").css("left", $(window).width() / 2 - $("#announce").outerWidth() / 2))
        })
    }

    function b() {
        $("#announce_do_not_show").is(":checked") ? c(function() {
            $("#announce").hide()
        }) : $("#announce").hide();
        return !1
    }

    function c(a) {
        chrome.storage.local.get("lightshot_announces", function(b) {
            b.lightshot_announces || (b.lightshot_announces = {});
            b.lightshot_announces["ann_" + f.id] = "do_not_show";
            chrome.storage.local.set(b,
                function() {
                    a()
                })
        })
    }

    function d(a) {
        chrome.storage.local.get("lightshot_announces", function(b) {
            var c = !0;
            "function" === typeof f.ra && (c = f.ra());
            b && b.lightshot_announces && "do_not_show" === b.lightshot_announces["ann_" + f.id] && (c = !1);
            a(c)
        })
    }
    var f = {
        id: "2",
        type: "update",
        text: P.d("screenshot_plugin_chrome_38_retina_bug"),
        ra: function() {
            var a = ia.Pa();
            return 38 != a && 39 != a || 1 == window.devicePixelRatio || 2 == window.devicePixelRatio ? !1 : !0
        }
    };
    $(function() {
        $("#announce_hide").click(b).html(P.d("screenshot_plugin_close"));
        $("#announce_close_cross").click(b);
        $("#announce_do_not_show_label").html(P.d("screenshot_plugin_announce_do_not_show"));
        a()
    })
})();

function la(a) {
    this.b = a
}
la.prototype.j = function() {
    return new x(this.b.width, this.b.height)
};

function Q(a, b) {
    var c = a.b.getBoundingClientRect(),
        d = L.aa(a.b);
    return new Rect({
        x: b.x * d.x + c.left + $(document).scrollLeft(),
        y: b.y * d.y + c.top + $(document).scrollTop(),
        c: b.c * d.x,
        a: b.a * d.y
    })
}

function ma(a, b) {
    var c = a.b.getBoundingClientRect(),
        d = L.aa(a.b);
    return new v(Math.round((b.x - c.left - $(document).scrollLeft()) / d.x), Math.round((b.y - c.top - $(document).scrollTop()) / d.y))
}

function R(a, b) {
    return ma(a, new v(b.pageX, b.pageY))
}

function na(a) {
    var b;
    b = document.createElement("canvas");
    b = document.getElementsByTagName("body")[0].appendChild(b);
    na.h.constructor.call(this, b);
    this.ua = a;
    L.Ga(this.b, this.ua);
    this.ha()
}
N.extend(na, la);
na.prototype.ha = function() {
    var a = $(this.ua);
    this.b.width = a.width();
    this.b.height = a.height();
    this.b.style.position = "absolute";
    this.b.style.left = a.offset().left + "px";
    this.b.style.top = a.offset().top + "px"
};

function oa(a) {
    var b = {
            X: "selectStart",
            w: "selectEnd",
            u: "redraw"
        },
        c = function() {
            function a() {
                d = new Rect;
                t = !1
            }

            function b(a) {
                d = a;
                t = !0;
                a = 3 * window.devicePixelRatio;
                var c = Math.floor(d.c / 2),
                    e = Math.floor(d.a / 2);
                k.right = K.t(new v(d.x + d.c, d.y + e), a);
                k.left = K.t(new v(d.x, d.y + e), a);
                k.top = K.t(new v(d.x + c, d.y), a);
                k.bottom = K.t(new v(d.x + c, d.y + d.a), a);
                k.topleft = K.t(new v(d.x, d.y), a);
                k.topright = K.t(new v(d.x + d.c, d.y), a);
                k.bottomleft = K.t(new v(d.x, d.y + d.a), a);
                k.bottomright = K.t(new v(d.x + d.c, d.y + d.a), a);
                k.move = d
            }

            function c(a) {
                if (t)
                    for (var b in k)
                        if (!a(k[b],
                                b)) break
            }
            var d = new Rect,
                t = !1,
                k = {},
                u = null;
            return {
                set: b,
                get: function() {
                    return d
                },
                clear: a,
                Ra: function() {
                    return t
                },
                ba: function(a) {
                    var b = "none";
                    t && c(function(c, d) {
                        var e = new Rect(c);
                        ba(e, 1);
                        return E(e, a) ? (b = d, !1) : !0
                    });
                    return b
                },
                cb: c,
                pa: function() {
                    u = d
                },
                restore: function() {
                    u ? b(u) : a()
                }
            }
        }(),
        d = function() {
            function a(b) {
                if (F) return !0;
                b = R(l, b);
                "move" === c.ba(b) && M();
                return !1
            }

            function d(a) {
                1 !== a.which && t();
                return !1
            }

            function e(a) {
                m = a = R(l, a);
                if (F) return !0;
                switch (D) {
                    case "left":
                    case "right":
                    case "top":
                    case "bottom":
                        c.set(K.Ua(y,
                            B, a));
                        break;
                    case "topleft":
                    case "topright":
                    case "bottomleft":
                    case "bottomright":
                        c.set(K.Aa(y, a));
                        break;
                    case "move":
                        var b = l.j();
                        c.set(new Rect({
                            G: Math.min(Math.max(a.x - r.left, 0), b.c),
                            I: Math.min(Math.max(a.y - r.top, 0), b.a),
                            H: Math.max(Math.min(a.x + r.right, b.c), 0),
                            J: Math.max(Math.min(a.y + r.bottom, b.a), 0)
                        }))
                }
                H();
                u(a);
                return !1
            }

            function g() {
                t();
                return !1
            }

            function t() {
                D = "none";
                B = y = r = null;
                var a = l.b;
                $(a).off("mouseup", g);
                $(a).off("mouseenter", d);
                c.get().l() ? (c.restore(), H()) : c.pa();
                z[b.w].fire({
                    rect: Q(l, c.get())
                })
            }

            function k(a) {
                if (1 != a.which || F) return !0;
                a = R(l, a);
                D = c.ba(a);
                switch (D) {
                    case "left":
                        y = G(c.get());
                        B = J(c.get());
                        break;
                    case "right":
                        y = da(c.get());
                        B = I(c.get());
                        break;
                    case "top":
                        y = I(c.get());
                        B = J(c.get());
                        break;
                    case "bottom":
                        y = da(c.get());
                        B = G(c.get());
                        break;
                    case "topleft":
                        y = J(c.get());
                        break;
                    case "topright":
                        y = I(c.get());
                        break;
                    case "bottomleft":
                        y = G(c.get());
                        break;
                    case "bottomright":
                        y = da(c.get());
                        break;
                    case "move":
                        var A = c.get();
                        r = {
                            left: a.x - A.x,
                            top: a.y - A.y,
                            right: A.x + A.c - a.x,
                            bottom: A.y + A.a - a.y
                        };
                        break;
                    case "none":
                        y =
                            a;
                        D = "bottomright";
                        break;
                    default:
                        alert("ERROR onMouseDown -> switch -> default")
                }
                a = l.b;
                $(a).on("mouseup", g);
                $(a).on("mouseenter", d);
                z[b.X].fire();
                return !1
            }

            function u(a) {
                var b = "none";
                "none" !== D ? b = D : a && (b = c.ba(a));
                a = l.b;
                switch (b) {
                    case "left":
                    case "right":
                        a.style.cursor = "ew-resize";
                        break;
                    case "top":
                    case "bottom":
                        a.style.cursor = "ns-resize";
                        break;
                    case "topright":
                    case "bottomleft":
                        a.style.cursor = "nesw-resize";
                        break;
                    case "topleft":
                    case "bottomright":
                        a.style.cursor = "nwse-resize";
                        break;
                    case "move":
                        a.style.cursor =
                            "move";
                        break;
                    default:
                        a.style.cursor = "default"
                }
            }

            function H() {
                z[b.u].fire(null)
            }

            function M() {
                var a = c.get(),
                    d = new Rect(new v(0, 0), l.j());
                a.isEqual(d) && q ? c.set(q) : (q = a, c.set(d));
                c.pa();
                H();
                z[b.w].fire({
                    rect: Q(l, c.get())
                })
            }
            var l = null,
                y = null,
                B = null,
                D = "none",
                r = null,
                q = null,
                z = {};
            z[b.X] = $.Callbacks();
            z[b.w] = $.Callbacks();
            z[b.u] = $.Callbacks();
            var F = !1,
                m = null,
                C = P.d("screenshot_plugin_tooltip");
            return {
                ca: function(b) {
                    l = new la(b);
                    H();
                    b = l.b;
                    $(b).on("mousedown", k);
                    $(b).on("mousemove", e);
                    $(b).on("dblclick", a)
                },
                clear: function() {
                    c.clear();
                    H()
                },
                r: function() {
                    return c.get()
                },
                o: b,
                attachEvent: function(a, b) {
                    "undefined" !== typeof z[a] && z[a].add(b)
                },
                detachEvent: function(a, b) {
                    "undefined" !== typeof z[a] && z[a].remove(b)
                },
                lock: function() {
                    F = !0;
                    l.b.style.cursor = "default";
                    D = "none"
                },
                Da: function() {
                    F = !1;
                    m && u(m)
                },
                U: function(a) {
                    if (a && a.getContext) {
                        var b = a.getContext("2d");
                        if (c.Ra()) {
                            var d = c.get();
                            b.fillStyle = "rgba(0, 0, 0, 0.5)";
                            b.fillRect(0, 0, a.width, d.y);
                            b.fillRect(0, d.y, d.x, a.height - d.y);
                            b.fillRect(d.x, d.y + d.a, a.width - d.x, a.height - d.y - d.a);
                            b.fillRect(d.x +
                                d.c, d.y, a.width - d.x - d.c, d.a);
                            b.lineWidth = 1 * window.devicePixelRatio;
                            b.lineJoin = "miter";
                            b.strokeStyle = "white";
                            O.fa(b, d.x, d.y, d.c, d.a);
                            b.strokeStyle = "black";
                            b.setLineDash([6]);
                            O.fa(b, d.x, d.y, d.c, d.a);
                            b.setLineDash([]);
                            b.fillStyle = "black";
                            b.strokeStyle = "white";
                            c.cb(function(a, c) {
                                "none" !== c && "move" !== c && (b.fillRect(a.x, a.y, a.c, a.a), O.fa(b, a.x, a.y, a.c, a.a));
                                return !0
                            });
                            var e = 14 * window.devicePixelRatio;
                            b.font = e + "px Helvetica";
                            b.fillStyle = "white";
                            b.textBaseline = "top";
                            a = d.c + "x" + d.a;
                            var f = new x(b.measureText(a).width,
                                    e),
                                e = 3 * window.devicePixelRatio,
                                f = new x(f.c + 2 * e, f.a + 2 * e),
                                u = null,
                                u = new Rect(new v(d.x, d.y - 5 * window.devicePixelRatio - f.a), f);
                            O.Va(b, u.x, u.y, u.c, u.a, 3 * window.devicePixelRatio, "rgba(0,0,0,0.8)", "rgba(0,0,0,0.8)");
                            b.fillText(a, u.x + e, u.y + e - 1 * window.devicePixelRatio)
                        } else b.fillStyle = "rgba(0, 0, 0, 0.5)", b.fillRect(0, 0, a.width, a.height), e = 50 * window.devicePixelRatio, b.font = e + "px Helvetica", b.fillStyle = "rgba(255, 255, 255, 0.5)", b.textBaseline = "top", f = new x(b.measureText(C).width, e), d = new Rect(new v, f), a = new Rect(new v,
                            new x(a.width, a.height)), fa(d, a), b.fillText(C, d.x, d.y)
                    }
                },
                Wa: M,
                offset: function(a, d) {
                    var e = new Rect(c.get());
                    e.x += a;
                    e.y += d;
                    var f = new Rect(new v(0, 0), l.j()),
                        e = ea(e, f);
                    e.size().isEqual(c.get().size()) && (c.set(e), H(), z[b.w].fire({
                        rect: Q(l, c.get())
                    }))
                },
                R: function(a, d) {
                    var e = new Rect(c.get());
                    e.c += a;
                    e.a += d;
                    if (!e.l()) {
                        var f = new Rect(new v(0, 0), l.j()),
                            e = ea(e, f);
                        c.set(e);
                        H();
                        z[b.w].fire({
                            rect: Q(l, c.get())
                        })
                    }
                }
            }
        }();
    d.ca(a);
    return d
};
var T = {
    ja: "default",
    Ea: "active"
};

function pa(a, b) {
    this.f = a;
    this.Ta = b;
    this.b = null;
    this.g = T.ja;
    this.Y()
}
pa.prototype.Y = function() {
    this.f.id = this.f.id || ga.Z("item_")
};

function qa(a, b) {
    a.g = b;
    if (a.b) {
        if (a.b) {
            var c = $(a.b),
                d;
            for (d in T) c.removeClass(T[d])
        }
        $(a.b).addClass(b)
    }
}

function ra(a, b) {
    ra.h.constructor.apply(this, arguments);
    this.b = document.createElement("div");
    this.b.id = this.f.id;
    this.b.className = "toolbar-separator"
}
N.extend(ra, pa);

function U(a, b) {
    U.h.constructor.apply(this, arguments);
    this.Y();
    this.na();
    sa(this)
}
N.extend(U, pa);
U.prototype.Y = function() {};
U.prototype.na = function() {
    this.b = document.createElement("div");
    this.b.id = this.f.id;
    this.b.title = this.f.caption;
    this.b.className = "toolbar-button " + this.f.className + " " + this.g
};

function sa(a) {
    $(a.b).on("click", function() {
        var b = a.Ta;
        b.B[b.K.n].fire(a.f.id);
        return !1
    });
    $(a.b).on("mousedown", !1)
}

function ta(a, b) {
    ta.h.constructor.apply(this, arguments);
    this.f.i(this)
}
N.extend(ta, U);
ta.prototype.na = function() {
    this.b = document.createElement("canvas");
    this.b.id = this.f.id;
    this.b.className = "toolbar-button-owner-draw";
    this.b.title = this.f.caption;
    this.b.width = 26 * window.devicePixelRatio;
    this.b.height = 27 * window.devicePixelRatio;
    this.b.getContext("2d").scale(window.devicePixelRatio, window.devicePixelRatio)
};

function ua(a) {
    this.s = a;
    this.C = [];
    this.B = {};
    this.B[this.K.n] = $.Callbacks();
    this.s.id = this.s.id || ga.Z("toolbar_");
    this.s.A = this.s.A || [];
    this.b = document.createElement("div");
    this.b.id = this.s.id;
    this.b.className = "toolbar " + this.s.className;
    document.getElementsByTagName("body")[0].appendChild(this.b);
    for (a = 0; a < this.s.A.length; a++) {
        var b;
        b = this.s.A[a];
        var c = null;
        "button" === b.type ? c = new U(b, this) : "button_owner_draw" === b.type ? c = new ta(b, this) : "separator" === b.type && (c = new ra(b, this));
        if (b = c) this.C.push(b),
            this.b.appendChild(b.b)
    }
}
n = ua.prototype;
n.K = {
    n: "buttonClicked"
};

function va(a, b, c) {
    null == c && "undefined" !== typeof b.x && "undefined" !== typeof b.y ? (a.b.style.left = b.x + "px", a.b.style.top = b.y + "px") : (a.b.style.left = b + "px", a.b.style.top = c + "px")
}
n.j = function() {
    return new x($(this.b).outerWidth(), $(this.b).outerHeight())
};
n.r = function() {
    var a = $(this.b).offset();
    return new Rect(new v(a.left, a.top), this.j())
};
n.hide = function() {
    $(this.b).hide()
};
n.show = function() {
    $(this.b).show()
};
n.attachEvent = function(a, b) {
    "undefined" !== typeof this.B[a] && this.B[a].add(b)
};
n.detachEvent = function(a, b) {
    "undefined" !== typeof this.B[a] && this.B[a].remove(b)
};

function wa(a) {
    for (var b = 0; b < a.C.length; b++) qa(a.C[b], T.ja)
}

function xa(a, b) {
    for (var c = 0; c < a.C.length; c++)
        if (a.C[c].f.id === b) return a.C[c];
    return null
};

function ya() {
    function a(a) {
        if ("share" === a)
            if ($(f.b).is(":visible")) f.hide();
            else {
                if (f.show(), a = (a = xa(d, "share")) ? a.b.getBoundingClientRect() : null) {
                    var b = f.j(),
                        g = a.left + (a.right - a.left) / 2;
                    a.bottom + 6 + b.a < $(window).innerHeight() ? (va(f, g - b.c / 2, a.bottom + 6), $(f.b).addClass("drop-down").removeClass("drop-up")) : (va(f, g - b.c / 2, a.top - 8 - b.a), $(f.b).addClass("drop-up").removeClass("drop-down"))
                }
            }
        else e[c.n].fire(a)
    }

    function b() {
        d.hide();
        f.hide();
        h.hide()
    }
    var c = {
            n: "buttonClicked"
        },
        d = null,
        f = null,
        h = null,
        e = {};
    e[c.n] =
        $.Callbacks();
    var g = ka.sa(window).display,
        t = {
            id: "toolbar_actions",
            className: "toolbar-horizontal",
            A: [{
                id: "upload",
                type: "button",
                caption: P.d("screenshot_plugin_upload") + " (" + g + "+D)",
                className: "button-upload"
            }, {
                type: "separator"
            }, {
                id: "close",
                type: "button",
                caption: P.d("screenshot_plugin_close") + " (" + g + "+X)",
                className: "button-close"
            }]
        },
        k = {
            id: "toolbar_share",
            className: "subtoolbar-horizontal",
            A: [{
                id: "share_twitter",
                type: "button",
                caption: P.d("screenshot_plugin_share_twitter"),
                className: "button-share-twitter"
            }, {
                id: "share_facebook",
                type: "button",
                caption: P.d("screenshot_plugin_share_facebook"),
                className: "button-share-facebook"
            }, {
                id: "share_vk",
                type: "button",
                caption: P.d("screenshot_plugin_share_vk"),
                className: "button-share-vk"
            }, {
                id: "share_pinterest",
                type: "button",
                caption: P.d("screenshot_plugin_share_pinterest"),
                className: "button-share-pinterest"
            }]
        },
        g = {
            id: "toolbar_edit",
            className: "toolbar-vertical",
            A: [{
                id: "pencil",
                type: "button",
                caption: P.d("screenshot_plugin_edit_pencil"),
                className: "button-pencil"
            }, {
                id: "line",
                type: "button",
                caption: P.d("screenshot_plugin_edit_line"),
                className: "button-line"
            }, {
                id: "arrow",
                type: "button",
                caption: P.d("screenshot_plugin_edit_arrow"),
                className: "button-arrow"
            }, {
                id: "rectangle",
                type: "button",
                caption: P.d("screenshot_plugin_edit_rect"),
                className: "button-rectangle"
            }, {
                id: "marker",
                type: "button",
                caption: P.d("screenshot_plugin_edit_marker"),
                className: "button-marker"
            }, {
                id: "text",
                type: "button",
                caption: P.d("screenshot_plugin_edit_text"),
                className: "button-text"
            }, {
                id: "color",
                type: "button_owner_draw",
                caption: P.d("screenshot_plugin_edit_color"),
                oa: {
                    color: "#ff0000"
                },
                i: function(a) {
                    var b = a.b;
                    if (b && b.getContext) {
                        var c = b.getContext("2d");
                        c.clearRect(0,
                            0, b.width, b.height);
                        c.fillStyle = a.f.oa.color;
                        c.fillRect(6, 5, 16, 17);
                        a = new Image;
                        a.src = "data:image/png;base64,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";
                        c.drawImage(a, .5, .5)
                    }
                }
            }, {
                type: "separator"
            }, {
                id: "undo",
                type: "button",
                caption: P.d("screenshot_plugin_edit_undo") + " (" + g + "+Z)",
                className: "button-undo"
            }]
        },
        d = new ua(t);
    d.attachEvent(d.K.n, a);
    f = new ua(k);
    f.attachEvent(f.K.n, a);
    h = new ua(g);
    h.attachEvent(h.K.n, a);
    b();
    return {
        ha: function(a) {
            var b = new Rect({
                    x: 0,
                    y: 0,
                    c: $(window).innerWidth(),
                    a: $(window).innerHeight()
                }),
                c = d.j(),
                e = [],
                f = d.j(),
                g = null,
                g = J(a);
            e.push(new v(Math.max(g.x - f.c, 0), g.y + 5));
            g = G(a);
            e.push(new v(Math.max(g.x - f.c, 0), g.y - 5 - f.a));
            g = I(a);
            e.push(new v(g.x -
                5 - f.c, g.y - f.a));
            g = J(a);
            e.push(new v(g.x + 5, g.y - f.a));
            g = J(a);
            e.push(new v(g.x - 5 - f.c, g.y - 5 - f.a));
            for (g = 0; g < e.length; g++)
                if (f = new Rect(e[g], c), ca(b, f)) {
                    va(d, e[g]);
                    break
                }
            var c = d.r(),
                e = h.j(),
                f = [],
                k = d.j(),
                r = h.j(),
                g = d.r(),
                q = null,
                q = J(a);
            f.push(new v(q.x + 5, Math.max(q.y - r.a, 0)));
            q = I(a);
            f.push(new v(q.x - 5 - r.c, Math.max(q.y - r.a, 0)));
            q = J(a);
            f.push(new v(q.x - 5 - r.c, Math.max(q.y - 5 - r.a, 0)));
            q = J(a);
            f.push(new v(g.x + g.c + 5, Math.max(q.y - 5 - r.a, 0)));
            q = I(a);
            f.push(new v(g.x - 5 - r.c, Math.max(q.y - r.a, 0)));
            q = J(a);
            f.push(new v(q.x -
                r.c, q.y + 5 + k.a + 5));
            q = G(a);
            f.push(new v(q.x - r.c, q.y - 5 - k.a - 5 - r.a));
            for (g = 0; g < f.length; g++)
                if (a = new Rect(f[g], e), ca(b, a) && ea(a, c).l()) {
                    va(h, f[g]);
                    break
                }
        },
        ta: b,
        Ca: function() {
            d.show();
            h.show()
        },
        o: c,
        attachEvent: function(a, b) {
            "undefined" !== typeof e[a] && e[a].add(b)
        },
        detachEvent: function(a, b) {
            "undefined" !== typeof e[a] && e[a].remove(b)
        },
        Ya: function(a, b) {
            wa(h);
            var c = xa(h, a);
            c && qa(c, b)
        },
        qa: function() {
            wa(h)
        },
        ga: function(a) {
            var b = xa(h, "color");
            b.f.oa.color = a;
            b.f.i(b)
        }
    }
};

function za(a) {
    a = a || {};
    var b = null,
        c = null,
        d = a.color || "#ff0000",
        f = a.width || 10,
        h = a.fontFamily || "Helvetica",
        c = document.createElement("textarea"),
        b = document.createElement("div");
    b.appendChild(c);
    b.style.lb = "999999";
    b.style.background = "none";
    b.style.border = "dashed black 1px";
    b.style.padding = 2 * window.devicePixelRatio + "px";
    b.style.margin = "2px";
    b.style.cursor = "move";
    c.style.background = "none";
    c.style.border = "none";
    c.style.outline = "none";
    c.style.resize = "none";
    c.style.padding = "0";
    c.style.margin = "0";
    c.style.color =
        d;
    c.style.font = f + "px " + h;
    document.getElementsByTagName("body")[0].appendChild(b);
    L.ea(b);
    L.Ba(b, a.za.x, a.za.y);
    aa(c);
    ja(b);
    c.focus();
    return {
        Oa: function() {
            return c ? c.value : null
        },
        Ma: function() {
            return b ? $(c).offset() : null
        },
        La: function() {
            return Number.parseInt(window.getComputedStyle(c).height) / c.rows
        },
        Xa: function() {
            b.parentNode.removeChild(b);
            c = b = null
        },
        D: function(a) {
            d = a;
            c.style.color = d
        },
        M: function(a) {
            f = a;
            c.style.fontSize = f + "px";
            $(c).change()
        }
    }
};

function Aa(a) {
    a = a || {};
    this.Sa = a.F || "line";
    this.p = a.color || "#ff0000";
    this.k = a.width || 10;
    this.ya = a.ib || 1;
    this.g = "new"
}
n = Aa.prototype;
n.i = function() {
    alert("not implemented")
};
n.setStart = function() {
    alert("not implemented")
};
n.setEnd = function() {
    alert("not implemented")
};
n.P = function() {
    alert("not implemented")
};
n.l = function() {
    alert("not implemented")
};
n.D = function() {};
n.M = function(a) {
    "drawing" == this.g && (this.k = a)
};

function Ba(a) {
    Ba.h.constructor.apply(this, arguments)
}
N.extend(Ba, Aa);

function V(a) {
    V.h.constructor.apply(this, arguments);
    this.q = this.v = null
}
N.extend(V, Ba);
V.prototype.setStart = function(a) {
    this.q = this.v = a;
    this.g = "drawing"
};
V.prototype.setEnd = function(a) {
    a && (this.q = a);
    this.g = "finished"
};
V.prototype.P = function(a) {
    "drawing" === this.g && (this.q = a)
};
V.prototype.l = function() {
    return null == this.v || null == this.q
};

function W(a) {
    W.h.constructor.apply(this, arguments);
    this.e = []
}
N.extend(W, Ba);
W.prototype.setStart = function(a) {
    this.e = [];
    this.e.push(a);
    this.g = "drawing"
};
W.prototype.setEnd = function(a) {
    a && this.e.push(a);
    this.g = "finished"
};
W.prototype.P = function(a) {
    if ("drawing" === this.g) {
        var b = this.e[this.e.length - 1];
        Math.sqrt(Math.pow(b.x - a.x, 2) + Math.pow(b.y - a.y, 2)) >= this.k / 8 && this.e.push(a)
    }
};
W.prototype.l = function() {
    return 0 == this.e.length
};

function Ca(a) {
    a = a || {};
    a.F = "line";
    Ca.h.constructor.apply(this, arguments)
}
N.extend(Ca, V);
Ca.prototype.i = function(a) {
    a.lineJoin = "round";
    a.lineCap = "round";
    a.strokeStyle = this.p;
    a.lineWidth = this.k * window.devicePixelRatio;
    a.beginPath();
    a.moveTo(this.v.x, this.v.y);
    a.lineTo(this.q.x, this.q.y);
    a.stroke()
};

function Ea(a) {
    a = a || {};
    a.F = "arrow";
    Ea.h.constructor.apply(this, arguments)
}
N.extend(Ea, V);
Ea.prototype.i = function(a) {
    a.lineJoin = "round";
    a.lineCap = "round";
    O.Ia(a, this.v.x, this.v.y, this.q.x, this.q.y, this.p, this.k * window.devicePixelRatio)
};

function Fa(a) {
    a = a || {};
    a.F = "rectangle";
    Fa.h.constructor.apply(this, arguments)
}
N.extend(Fa, V);
Fa.prototype.i = function(a) {
    a.lineJoin = "round";
    a.lineCap = "round";
    a.strokeStyle = this.p;
    a.lineWidth = this.k * window.devicePixelRatio;
    var b = K.Aa(this.v, this.q);
    a.strokeRect(b.x, b.y, b.c, b.a)
};

function X(a) {
    a = a || {};
    a.F = "pencil";
    X.h.constructor.apply(this, arguments)
}
N.extend(X, W);
X.prototype.i = function(a) {
    a.lineJoin = "round";
    a.lineCap = "round";
    a.strokeStyle = this.p;
    a.lineWidth = this.k * window.devicePixelRatio;
    if (1 == this.e.length || 2 == this.e.length && this.e[0].isEqual(this.e[1])) a.fillStyle = this.p, a.beginPath(), a.arc(this.e[0].x, this.e[0].y, this.k / 2 * window.devicePixelRatio, 0, 2 * Math.PI, !1), a.fill();
    else {
        a.beginPath();
        a.moveTo(this.e[0].x, this.e[0].y);
        for (var b = 1; b < this.e.length; b++) a.lineTo(this.e[b].x, this.e[b].y);
        a.stroke()
    }
};

function Y(a) {
    a = a || {};
    a.F = "marker";
    Y.h.constructor.apply(this, arguments);
    this.ya = .5
}
N.extend(Y, X);
Y.prototype.i = function(a) {
    var b = a.globalAlpha;
    a.globalAlpha = this.ya;
    Y.h.i.apply(this, arguments);
    a.globalAlpha = b
};

function Text(a) {
    a = a || {};
    a.F = "text";
    Text.h.constructor.apply(this, arguments);
    this.va = a.canvas;
    this.m = null;
    this.da = "";
    this.T = null;
    this.wa = "Helvetica";
    this.xa = 0
}
N.extend(Text, Aa);
n = Text.prototype;
n.i = function(a) {
    if ("drawing" !== this.g && "finished" === this.g) {
        a.font = this.k * window.devicePixelRatio + "px " + this.wa;
        a.fillStyle = this.p;
        a.textBaseline = "top";
        for (var b = this.da.split("\n"), c = 0; c < b.length; c++) a.fillText(b[c], this.T.x, this.T.y + c * this.xa)
    }
};
n.setStart = function() {};
n.setEnd = function(a) {
    if (a) {
        var b, c = this.va;
        b = c.b.getBoundingClientRect();
        c = L.aa(c.b);
        b = new v(a.x * c.x + b.left + $(document).scrollLeft(), a.y * c.y + b.top + $(document).scrollTop());
        this.m = za({
            za: b,
            color: this.p,
            width: this.k * window.devicePixelRatio,
            fontFamily: this.wa
        });
        this.T = a
    }
    this.g = "drawing"
};
n.P = function() {};
n.l = function() {
    return 0 == this.da.length
};
n.D = function(a) {
    this.p = a;
    this.m && this.m.D(this.p)
};
n.M = function(a) {
    this.k = a;
    this.m && this.m.M(this.k * window.devicePixelRatio)
};

function Ga(a) {
    function b() {
        s = null;
        k()
    }

    function c(a) {
        if (!u() || q === l.L) return !0;
        a = R(z, a);
        m && m.P(a);
        s = a;
        k();
        return !1
    }

    function d(a) {
        1 != a.which && h(null);
        return !1
    }

    function f(a) {
        if (1 != a.which) return !0;
        a = a ? R(z, a) : null;
        h(a);
        return !1
    }

    function h(a) {
        var b = z.b;
        $(b).off("mouseup", f);
        $(b).off("mouseenter", d);
        m && m.setEnd(a);
        k();
        C[y.V].fire()
    }

    function e(a) {
        if (1 != a.which || !u()) return !0;
        g();
        var b = {
            color: B,
            width: t()
        };
        switch (q) {
            case l.ka:
                m = new Ca(b);
                break;
            case l.ia:
                m = new Ea(b);
                break;
            case l.ma:
                m = new Fa(b);
                break;
            case l.la:
                m =
                    new X(b);
                break;
            case l.O:
                b.color = D;
                m = new Y(b);
                break;
            case l.L:
                b.canvas = z;
                m = new Text(b);
                break;
            default:
                console.log("_startNewObject: no such tool")
        }
        m && (a = R(z, a), m.setStart(a));
        k();
        a = z.b;
        $(a).on("mouseup", f);
        $(a).on("mouseenter", d);
        C[y.W].fire();
        return !1
    }

    function g() {
        if (m) {
            if (m.Sa === l.L) {
                var a = m;
                a.da = a.m.Oa();
                a.xa = a.m.La();
                var b = a.m.Ma();
                a.T = ma(a.va, new v(b.left, b.top));
                a.m.Xa();
                a.m = null;
                a.g = "finished";
                k()
            }
            m.l() || F.push(m);
            m = null
        }
    }

    function t() {
        var a = 0;
        switch (q) {
            case l.ka:
            case l.ia:
            case l.ma:
            case l.la:
                a =
                    2 * r + 3;
                break;
            case l.O:
                a = 2 * r + 16;
                break;
            case l.L:
                a = 4 * r + 16
        }
        return a
    }

    function k() {
        C[y.u].fire(null)
    }

    function u() {
        return null !== q
    }

    function H() {
        M(null);
        k()
    }

    function M(a) {
        g();
        q = a
    }
    var l = {
            la: "pencil",
            ka: "line",
            ia: "arrow",
            ma: "rectangle",
            O: "marker",
            L: "text"
        },
        y = {
            W: "selectStart",
            V: "selectEnd",
            u: "redraw"
        },
        B = localStorage.mainColor || "#ff0000",
        D = localStorage.markerColor || "#ffff00",
        r = 0,
        q = null,
        z = new la(a),
        F = [],
        m = null,
        C = {},
        s = null;
    C[y.W] = $.Callbacks();
    C[y.V] = $.Callbacks();
    C[y.u] = $.Callbacks();
    (function() {
        var a = z.b;
        $(a).on("mousedown",
            e);
        $(a).on("mousemove", c);
        $(a).on("mouseleave", b)
    })();
    return {
        $a: M,
        D: function(a) {
            q === l.O ? (D = a, localStorage.markerColor = D) : (B = a, localStorage.mainColor = B);
            m && m.D(a)
        },
        Q: function() {
            return q === l.O ? D : B
        },
        ab: H,
        S: u,
        Ka: function() {
            return q
        },
        U: function(a) {
            if (a && a.getContext) {
                a = a.getContext("2d");
                for (var b = 0; b < F.length; b++) F[b].i(a);
                m && m.i(a);
                u() && q !== l.L && s && (b = t(), a.lineJoin = "round", a.strokeStyle = "black", a.lineWidth = 1 * window.devicePixelRatio, a.beginPath(), a.arc(s.x, s.y, b / 2 * window.devicePixelRatio, 0, 2 * Math.PI, !0), a.stroke())
            }
        },
        bb: function() {
            g();
            F.pop();
            0 === F.length && H();
            k()
        },
        Ha: function() {
            u() && 0 < r && (r -= 1, m && m.M(t()), k())
        },
        Qa: function() {
            u() && 10 > r && (r += 1, m && m.M(t()), k())
        },
        eb: l,
        o: y,
        attachEvent: function(a, b) {
            "undefined" !== typeof C[a] && C[a].add(b)
        },
        detachEvent: function(a, b) {
            "undefined" !== typeof C[a] && C[a].remove(b)
        }
    }
};
var Ha = function(a) {
    (function() {
        window._gaq.push(["_setAccount", a]);
        window._gaq.push(["_trackPageview"]);
        var b = document.createElement("script");
        b.type = "text/javascript";
        b.async = !0;
        b.src = "https://ssl.google-analytics.com/ga.js";
        var c = document.getElementsByTagName("script")[0];
        c.parentNode.insertBefore(b, c)
    })();
    return {
        N: function(a, c, d, f, h) {
            window._gaq.push(["_trackEvent", a, c, d, f, h])
        }
    }
}("UA-53060756-1");

function Ia() {
    function a(a) {
        var b = document.createElement("canvas");
        b.width = a.c;
        b.height = a.a;
        var h = b.getContext("2d"),
            e = new Image;
        e.src = c;
        h.drawImage(e, a.x, a.y, a.c, a.a, 0, 0, a.c, a.a);
        return b
    }
    var b = null,
        c = null;
    return {
        load: function(a, f) {
            b = a;
            chrome.runtime.sendMessage({
                name: "load_screenshot",
                id: b
            }, function(a) {
                c = a;
                f(c)
            })
        },
        fb: function(b) {
            return a(b).toDataURL()
        },
        Ja: a
    }
}
var Z = function() {
        function a() {
            window.close()
        }
        return {
            close: a,
            upload: function(b) {
                b.dataUrl && ia.Za("upload_scrn_", b, function(b) {
                    chrome.runtime.sendMessage({
                        name: "upload_screenshot",
                        id: b
                    }, function() {
                        a()
                    })
                })
            },
            save: function(b) {
                b && chrome.downloads.download({
                    url: b,
                    filename: "Screenshot.png",
                    saveAs: !0
                }, function() {
                    a()
                })
            },
            Fa: function(a) {
            	//
            },
            print: function(a) {
                if (a) {
                    var c = document.createElement("iframe");
                    c.style.visibility = "hidden";
                    c.style.position = "fixed";
                    c.style.width = "0";
                    c.style.height = "0";
                    c.style.right = "0";
                    c.style.bottom = "0";
                    c.onload = function() {
                        var d = c.contentWindow.document,
                            f = d.getElementsByTagName("body")[0];
                        f.style.margin = "0";
                        f.style.padding = "0";
                        f.style.textAlign = "center";
                        d = d.createElement("img");
                        d.src = a;
                        L.ea(d);
                        f.appendChild(d);
                        c.contentWindow.print()
                    };
                    document.getElementsByTagName("body")[0].appendChild(c)
                }
            }
        }
    }(),
    Ja = function() {
        function a() {
            $(window).on("mousewheel", function(a) {
                w.S() && (0 < a.deltaY ? c() : 0 > a.deltaY && d())
            });
            $(window).on("contextmenu", !1)
        }

        function b() {
            function a(b, c) {
                $(window).on("keydown", null, b, c)
            }

            function b(a, c) {
                $(window).on("keydown", null, a, c);
                $(document).on("keydown", "textarea", a, c)
            }
            var g = ka.sa(window).id;
            b("esc", f);
            b(g + "+=", d);
            b(g + "+-", c);
            b(g + "+s", function() {
                y();
                return !1
            });
            b(g + "+x", function() {
                e();
                Z.close();
                return !1
            });
            b(g + "+d", function() {
                B();
                return !1
            });
            b(g +
                "+p", function() {
                l();
                return !1
            });
            b(g + "+z", function() {
                M();
                return !1
            });
            a(g + "+a", function() {
                s.Wa();
                return !1
            });
            a("up", function() {
                s.offset(0, -1);
                return !1
            });
            a("down", function() {
                s.offset(0, 1);
                return !1
            });
            a("left", function() {
                s.offset(-1, 0);
                return !1
            });
            a("right", function() {
                s.offset(1, 0);
                return !1
            });
            a("shift+up", function() {
                s.R(0, -1);
                return !1
            });
            a("shift+down", function() {
                s.R(0, 1);
                return !1
            });
            a("shift+left", function() {
                s.R(-1, 0);
                return !1
            });
            a("shift+right", function() {
                s.R(1, 0);
                return !1
            })
        }

        function c() {
            w.Ha();
            return !1
        }

        function d() {
            w.Qa();
            return !1
        }

        function f() {
            w.S() ?
                e() : Z.close()
        }

        function h(a) {
            switch (a) {
                case "close":
                    e();
                    Z.close();
                    break;
                case "upload":
                    B();
                    break;
                case "save":
                    y();
                    break;
                case "copy":
                    e();
                    Z.Fa(r());
                    Ha.N("action", "copy");
                    break;
                case "print":
                    l();
                    break;
                case "search_google":
                    B("search_google");
                    break;
                case "share_twitter":
                    B("share_twitter");
                    break;
                case "share_facebook":
                    B("share_facebook");
                    break;
                case "share_vk":
                    B("share_vk");
                    break;
                case "share_pinterest":
                    B("share_pinterest");
                    break;
                case "pencil":
                case "line":
                case "arrow":
                case "rectangle":
                case "marker":
                case "text":
                    w.S() &&
                        w.Ka() === a ? e() : (w.$a(a), A.Ya(a, T.Ea), A.ga(w.Q()), s.lock(), Ha.N("edit", "tool_click", a));
                    break;
                case "undo":
                    M()
            }
        }

        function e() {
            w.ab();
            A.qa();
            s.Da()
        }

        function g(a) {
            var b = S.b;
            b && b.getContext && (b.getContext("2d").clearRect(0, 0, b.width, b.height), w.U(b, a), s.U(b, a))
        }

        function t() {
            A.Ca()
        }

        function k() {
            A.ta()
        }

        function u(a) {
            a.rect.l() || (A.Ca(), A.ha(a.rect))
        }

        function H() {
            A.ta()
        }

        function M() {
            w.bb();
            w.S() || (A.qa(), s.Da())
        }

        function l() {
            e();
            Z.print(r());
            Ha.N("action", "print")
        }

        function y() {
            e();
            Z.save(r());
            Ha.N("action",
                "save")
        }

        function B(a) {
            e();
            Z.upload(D(a));
            Ha.N("action", "upload", a)
        }

        function D(a) {
            var b = {
                dataUrl: r(),
                size: s.r().size(),
                dpr: window.devicePixelRatio
            };
            a && (b.cmdAfterUpload = a);
            return b
        }

        function r() {
            if (s.r().l()) return null;
            var a = C.Ja(s.r()),
                b = s.r();
            a.getContext("2d").translate(-b.x, -b.y);
            w.U(a, null);
            return a.toDataURL()
        }

        function q() {
            $("#color").colpick({
                colorScheme: "dark",
                layout: "rgbhex",
                color: w.Q(),
                onShow: function(a) {
                    $("#color").colpickSetColor(w.Q(), !0);
                    var b = J(Q(S, s.r())),
                        c = Math.max(b.x - 3 - $(a).width(),
                            0),
                        b = Math.max(b.y - 3 - $(a).height(), 0);
                    $(a).css({
                        left: c + "px",
                        top: b + "px"
                    })
                },
                onSubmit: function(a, b, c, d) {
                    a = "#" + b;
                    A.ga(a);
                    w.D(a);
                    $(d).colpickHide()
                }
            });
            $(S.b).on("mousedown", function() {
                $("#color").colpickHide()
            });
            A.ga(w.Q())
        }

        function z(a) {
            if (m.complete) a && a();
            else $(m).on("load", function Da() {
                $(m).off("load", Da);
                a && a()
            })
        }

        function F(a) {
            var b = document.getElementById("content");
            b && (m = document.createElement("img"), m.src = a, L.ea(m), b.appendChild(m))
        }
        var m = null,
            C = null,
            s = null,
            A = null,
            w = null,
            S = null;
        return {
            ca: function() {
                A =
                    ya();
                A.attachEvent(A.o.n, h);
                C = Ia();
                C.load(ha.Na("id"), function(c) {
                    F(c);
                    z(function() {
                        S = new na(m);
                        w = Ga(S.b);
                        w.attachEvent(w.o.W, k);
                        w.attachEvent(w.o.V, t);
                        w.attachEvent(w.o.u, g);
                        s = oa(S.b);
                        s.attachEvent(s.o.X, H);
                        s.attachEvent(s.o.w, u);
                        s.attachEvent(s.o.u, g);
                        s.clear();
                        q();
                        b();
                        a()
                    })
                })
            }
        }
    }();

// Add code to interface with Blt sizzle time tracking
function startBltSizzleTimer(issueId) {
    // Make an API call to start the timer for the given issue
    fetch(`https://blt-sizzle-api.example.com/start-timer?issueId=${issueId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    }).then(response => {
        if (response.ok) {
            console.log('Timer started for issue:', issueId);
        } else {
            console.error('Failed to start timer for issue:', issueId);
        }
    }).catch(error => {
        console.error('Error starting timer for issue:', issueId, error);
    });
}

function stopBltSizzleTimer(issueId) {
    // Make an API call to stop the timer for the given issue
    fetch(`https://blt-sizzle-api.example.com/stop-timer?issueId=${issueId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    }).then(response => {
        if (response.ok) {
            console.log('Timer stopped for issue:', issueId);
        } else {
            console.error('Failed to stop timer for issue:', issueId);
        }
    }).catch(error => {
        console.error('Error stopping timer for issue:', issueId, error);
    });
}

// Implement an in-progress indicator on the top right of github.com
function showInProgressIndicator() {
    const indicator = document.createElement('div');
    indicator.id = 'blt-sizzle-indicator';
    indicator.style.position = 'fixed';
    indicator.style.top = '10px';
    indicator.style.right = '10px';
    indicator.style.backgroundColor = 'red';
    indicator.style.color = 'white';
    indicator.style.padding = '5px';
    indicator.style.zIndex = '9999';
    indicator.innerText = 'In Progress';
    document.body.appendChild(indicator);
}

function hideInProgressIndicator() {
    const indicator = document.getElementById('blt-sizzle-indicator');
    if (indicator) {
        document.body.removeChild(indicator);
    }
}

// Add functionality to Quickstart on any issue and have the timer stop and start based on the current issue in the browser
function quickstartIssue(issueId) {
    startBltSizzleTimer(issueId);
    showInProgressIndicator();
}

function stopIssue(issueId) {
    stopBltSizzleTimer(issueId);
    hideInProgressIndicator();
}

// Listen for changes in the URL to detect when the user navigates to a different issue
let currentIssueId = null;
setInterval(() => {
    const issueIdMatch = window.location.pathname.match(/\/issues\/(\d+)/);
    const issueId = issueIdMatch ? issueIdMatch[1] : null;

    if (issueId !== currentIssueId) {
        if (currentIssueId) {
            stopIssue(currentIssueId);
        }
        if (issueId) {
            quickstartIssue(issueId);
        }
        currentIssueId = issueId;
    }
}, 1000);

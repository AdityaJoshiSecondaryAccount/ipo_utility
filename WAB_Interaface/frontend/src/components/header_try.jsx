<>
    {"{"}% load static %{"}"}
    {"{"}% load pwa %{"}"}
    {"{"}% progressive_web_app_meta %{"}"}
    {/* OLD Required meta tags */}
    {/* <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no"> */}
    {/* NEW Required meta tags */}
    <meta charSet="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    {/* OLD Bootstrap CSS */}
    <link rel="stylesheet" href="{% static  'CSS/bootstrap.min.css' %}" />
    <link rel="stylesheet" href="{% static  'CSS/font-awesome.min.css' %}" />
    <link rel="stylesheet" href="{% static  'CSS/jquery-ui.css' %}" />
    <link rel="stylesheet" href="{% static  'CSS/loader.css' %}" />
    {/* <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.2/css/all.min.css" /> */}
    <title>
        {"{"}% block title%{"}"} {"{"}% endblock %{"}"}
    </title>
    {"{"}% block css %{"}"} {"{"}% endblock %{"}"}
    <style
        dangerouslySetInnerHTML={{
            __html:
                "\n        .fixed-top {\n            position: fixed;\n            top: 0;\n            right: 0;\n            left: 0;\n            z-index: 1030;\n        }\n\n        .footer {\n            z-index: 999;\n        }\n\n        .navbar-dark .navbar-nav .active>.nav-link,\n        .navbar-dark .navbar-nav .nav-link.active,\n        .navbar-dark .navbar-nav .nav-link.show,\n        .navbar-dark .navbar-nav .show>.nav-link {\n            color: white;\n        }\n\n        .user-dropdown {\n            left: -71px !important;\n        }\n\n        .navbar-expand-md .navbar-nav .dropdown-menu {\n            position: absolute;\n            background: #686868;\n            color: white;\n            margin-top: -2.875px;\n            margin-left: 0px;\n            cursor: pointer;\n        }\n\n        .navbar-expand-md .navbar-nav .logout {\n            margin-top: 11.125px;\n            margin-left: 4px;\n        }\n\n        .dropdown-menu {\n            top: 100%;\n            left: 0;\n            z-index: 1000;\n            display: none;\n            min-width: 10rem;\n            padding: .5rem 0;\n            margin: .125rem 0 0;\n            font-size: 1rem;\n            text-align: left;\n            list-style: none;\n            border: 1px solid rgba(0, 0, 0, .15);\n            border-radius: .25rem;\n        }\n\n\n        .dropdown-item {\n            display: block;\n            width: 100%;\n            padding: .25rem 1.5rem;\n            clear: both;\n            font-weight: 400;\n            color: white;\n            text-align: inherit;\n            white-space: nowrap;\n            background-color: transparent;\n            border: 0;\n        }\n\n        a {\n            color: black;\n            text-decoration: none;\n            background-color: transparent;\n\n        }\n\n        a:not([href]):not([tabindex]):focus,\n        a:not([href]):not([tabindex]):hover {\n            color: inherit;\n            text-decoration: none;\n            color: black;\n        }\n\n\n        /* Changepassword MODAL */\n        .addipomodal {\n            margin: 0% 2%;\n            position: fixed;\n        }\n\n        .modal-dialog1 {\n            max-width: 46%;\n            margin: 1.75rem auto;\n        }\n\n        /* MODAL CSS */\n        /* * {\n            margin: 0;\n            padding: 0;\n            box-sizing: border-box;\n            font-family: arabic typesetting;\n        } */\n\n        .background {\n\n            overflow: hidden;\n            border-radius: 28px;\n        }\n\n        ::selection {\n            background: rgba(26, 188, 156, 0.3);\n        }\n\n        /* .container {\n            max-width: 440px;\n            padding: 0 20px;\n            margin: 170px auto;\n        } */\n\n        /* .wrapper {\n            width: 100%;\n            background: rgba(0, 0, 0, 0.48);\n            border-radius: 5px;\n            box-shadow: 0px 4px 10px 1px rgba(0, 0, 0, 0.1);\n        }  */\n\n        .wrapper .title {\n            height: 75px;\n            /* background: #16a085; */\n            border-radius: 5px 5px 0 0;\n            color: black;\n            font-size: 31px;\n            font-weight: 609;\n            display: flex;\n            align-items: center;\n            justify-content: center;\n\n        }\n\n        .wrapper form {\n            padding: 0px 25px 25px 25px;\n        }\n\n        .wrapper form .row {\n            height: 45px;\n            margin-bottom: 15px;\n            position: relative;\n        }\n\n        .wrapper form .row input {\n            height: 100%;\n            width: 100%;\n            outline: none;\n            padding-left: 60px;\n            border-radius: 5px;\n            border: 1px solid lightgrey;\n            font-size: 16px;\n            transition: all 0.3s ease;\n        }\n\n        form .row input:focus {\n            border-color: #16a085;\n            box-shadow: inset 0px 0px 2px 2px rgba(26, 188, 156, 0.25);\n        }\n\n        form .row input::placeholder {\n            color: #999;\n        }\n\n        .wrapper form .row i {\n            position: absolute;\n            width: 47px;\n            height: 100%;\n            color: #fff;\n            font-size: 18px;\n            background: #5cb85c;\n            border: 1px solid #4cae4c;\n            border-radius: 5px 0 0 5px;\n            display: flex;\n            align-items: center;\n            justify-content: center;\n        }\n\n        .wrapper form .pass {\n            margin: -8px 0 20px 0;\n        }\n\n        .wrapper form .pass a {\n            color: white;\n            font-size: 19px;\n            text-decoration: none;\n        }\n\n        .wrapper form .pass a:hover {\n            text-decoration: underline;\n        }\n\n        .wrapper form .button input {\n            color: #fff;\n            font-size: 20px;\n            font-weight: 500;\n            padding-left: 0px;\n            background: green;\n            border: none;\n            cursor: pointer;\n            border-radius: 50px;\n        }\n\n        /* form .button input:hover{\n        background: #12876f;\n        } */\n        .wrapper form .signup-link {\n            text-align: center;\n            margin-top: 20px;\n            font-size: 17px;\n        }\n\n        .wrapper form .signup-link a {\n            color: whitesmoke;\n            text-decoration: none;\n        }\n\n        form .signup-link a:hover {\n            text-decoration: underline;\n        }\n\n        ::placeholder {\n            font-size: 1.0em;\n            font-weight: bold;\n        }\n\n        .modal1 {\n            display: none;\n            margin: 8% 0%;\n            padding: 0% 0%;\n            position: fixed;\n\n        }\n\n        .field-icon1 {\n            float: right;\n            margin-left: -31px;\n            margin-top: 13px;\n            position: relative;\n            z-index: 2;\n        }\n\n        .field-icon2 {\n            float: right;\n            margin-left: -31px;\n            margin-top: 13px;\n            position: relative;\n            z-index: 2;\n        }\n\n        @media (min-width: 992px) and (max-width: 41991px) {\n            .chng-box {\n                margin-right: 0rem !important;\n            }\n\n            .title {\n                padding: 0px 9px !important;\n            }\n        }\n\n        @media (min-width: 768px) and (max-width: 991px) {\n            .chng-box {\n                margin-left: 11rem;\n            }\n\n            .title {\n                padding: 0px 9px !important;\n            }\n        }\n\n        @media (min-width: 722px) and (max-width: 767px) {\n            .chng-box {\n                margin-left: 1rem;\n            }\n\n            .title {\n                padding: 0px 9px !important;\n            }\n\n            .addipomodal {\n                margin: 0% -50.5% !important;\n                width: 198%;\n            }\n\n            .wrapper form .row input {\n                padding-left: 50px !important;\n                font-size: 14px;\n            }\n\n            .wrapper form {\n                padding: 0px 0px 0px 0px !important;\n            }\n        }\n\n        @media (min-width: 666px) and (max-width: 721px) {\n            .chng-box {\n                margin-left: 1rem;\n            }\n\n            .title {\n                padding: 0px 9px !important;\n            }\n\n            .addipomodal {\n                margin: -2% -46.5% !important;\n                width: 193%;\n            }\n\n            .wrapper form .row input {\n                padding-left: 50px !important;\n                font-size: 14px;\n            }\n\n            .wrapper form {\n                padding: 0px 0px 0px 0px !important;\n            }\n        }\n\n        @media (min-width: 616px) and (max-width: 665px) {\n            .chng-box {\n                margin-left: 1rem;\n            }\n\n            .title {\n                padding: 0px 9px !important;\n            }\n\n            .addipomodal {\n                margin: -2% -49.5% !important;\n                width: 193%;\n            }\n\n            .wrapper form .row input {\n                padding-left: 50px !important;\n                font-size: 14px;\n            }\n\n            .wrapper form {\n                padding: 0px 0px 0px 0px !important;\n            }\n        }\n\n        @media (min-width: 558px) and (max-width: 615px) {\n            .chng-box {\n                margin-left: 1rem;\n            }\n\n            .title {\n                padding: 0px 9px !important;\n            }\n\n            .addipomodal {\n                margin: -2% -48.5% !important;\n                width: 193%;\n            }\n\n            .wrapper form .row input {\n                padding-left: 50px !important;\n                font-size: 14px;\n            }\n\n            .wrapper form {\n                padding: 0px 0px 0px 0px !important;\n            }\n        }\n\n        @media (min-width: 503px) and (max-width: 557px) {\n            .chng-box {\n                margin-left: 1rem;\n            }\n\n            .title {\n                padding: 0px 9px !important;\n            }\n\n            .addipomodal {\n                margin: -2% -48.5% !important;\n                width: 193%;\n            }\n\n            .wrapper form .row input {\n                padding-left: 50px !important;\n                font-size: 14px;\n            }\n\n            .wrapper form {\n                padding: 0px 0px 0px 0px !important;\n            }\n        }\n\n        @media (min-width: 451px) and (max-width: 502px) {\n            .chng-box {\n                margin-left: 1rem;\n            }\n\n            .title {\n                padding: 0px 9px !important;\n            }\n\n            .addipomodal {\n                margin: -2% -48.5% !important;\n                width: 193%;\n            }\n\n            .wrapper form .row input {\n                padding-left: 50px !important;\n                font-size: 14px;\n            }\n\n            .wrapper form {\n                padding: 0px 0px 0px 0px !important;\n            }\n        }\n\n        @media (min-width: 411px) and (max-width: 450px) {\n            .chng-box {\n                margin-left: 0.5rem;\n            }\n\n            .title {\n                padding: 0px 9px !important;\n            }\n\n            .addipomodal {\n                margin: -2% -48.5% !important;\n                width: 193%;\n            }\n\n            .wrapper form .row input {\n                padding-left: 50px !important;\n                font-size: 14px;\n            }\n\n            .wrapper form {\n                padding: 0px 0px 0px 0px !important;\n            }\n        }\n\n        @media (min-width: 390px) and (max-width: 410px) {\n            .chng-box {\n                margin-left: 1rem;\n            }\n\n            .title {\n                padding: 0px 9px !important;\n            }\n\n            .addipomodal {\n                margin: -2% -48.5% !important;\n                width: 193%;\n            }\n\n            .wrapper form .row input {\n                padding-left: 50px !important;\n                font-size: 14px;\n            }\n\n            .wrapper form {\n                padding: 0px 0px 0px 0px !important;\n            }\n        }\n\n        .expiry-message {\n            padding: 10px;\n            background-color: #f8d7da;\n            color: #721c24;\n            border: 1px solid #f5c6cb;\n            border-radius: 4px;\n            margin: 10px 0;\n            display: none;\n            /* Initially hidden */\n        }\n    "
        }}
    />
    <div className="loader">
        <div className="loader-style-4" />
    </div>
    {/* NEW NAVBAR */}
    <nav
        className="navbar navbar-expand-md navbar-dark justify-content-center fixed-top"
        style={{ background: "#686868", position: "fixed" }}
    >
        {/* <a class="navbar-brand abs" href="#" style="color: white; cursor:unset;"> IPO UTILITY
  </a> */}
        <button
            className="navbar-toggler navbar-toggler-right"
            type="button"
            data-toggle="collapse"
            data-target="#navbarNavAltMarkup"
            aria-controls="navbarNavAltMarkup"
            aria-expanded="false"
            aria-label="Toggle navigation"
        >
            <span className="navbar-toggler-icon" />
        </button>
        {"{"}% comment %{"}"}{" "}
        <div className="expiry-message collapse fixed-top" id="expiry-message">
            <span>
                Your account expires on: {"{"}
                {"{"} expiry_date {"}"}
                {"}"}.
            </span>
            <button
                type="button"
                className="close"
                data-bs-toggle="collapse"
                data-bs-target="#expiry-message"
                aria-label="Close"
                style={{ fontSize: 20 }}
            >
                X
            </button>
            {"{"}% comment %{"}"}{" "}
            <button className="close-btn" id="close-btn">
                ×
            </button>
        </div>{" "}
        {"{"}% endcomment %{"}"}
        <div
            className="expiry-message fixed-top"
            id="expiry-message"
            style={{ marginBottom: "-8px", marginTop: 0 }}
        >
            <span>
                Your account expires on: {"{"}
                {"{"} expiry_date {"}"}
                {"}"}.
            </span>
            <button
                type="button"
                className="close"
                id="close-btn"
                aria-label="Close"
                style={{ fontSize: 20 }}
            >
                X
            </button>
        </div>
        <div
            className="collapse navbar-collapse"
            id="navbarNavAltMarkup"
            style={{ marginBottom: "-8px", marginTop: "-15px" }}
        >
            <ul className="navbar-nav" style={{ marginBottom: "-3px" }}>
                {"{"}% comment %{"}"}{" "}
                <li className="nav-item active">
                    <b>
                        {" "}
                        <a
                            className="nav-link"
                            href="/"
                            style={{ color: "orange", marginBottom: "-4px" }}
                        >
                            {" "}
                            <img
                                src="/../static/image/home.png"
                                width="23px"
                                height="23px"
                                style={{ marginBottom: 5 }}
                            />
                            IPO UTILITY{" "}
                        </a>
                    </b>
                    {/* <a class="nav-link" href="#" style="color: white; cursor:unset;"> IPO UTILITY</a> */}
                </li>{" "}
                {"{"}% endcomment %{"}"}
                {"{"}% if request.user.is_authenticated %{"}"}
                <li className="nav-item active">
                    <b>
                        <a
                            className="nav-link"
                            href="/"
                            style={{ color: "orange", marginBottom: "-4px" }}
                        >
                            <img
                                src="{% static 'image/home.png' %}"
                                width="23px"
                                height="23px"
                                style={{ marginBottom: 5 }}
                            />
                            IPO UTILITY
                        </a>
                    </b>
                </li>
                {"{"}% else %{"}"}
                <li className="nav-item active">
                    <b>
                        <span
                            className="nav-link"
                            style={{
                                color: "orange",
                                marginBottom: "-4px",
                                cursor: "default"
                            }}
                        >
                            <img
                                src="{% static 'image/home.png' %}"
                                width="23px"
                                height="23px"
                                style={{ marginBottom: 5 }}
                            />
                            IPO UTILITY
                        </span>
                    </b>
                </li>
                {"{"}% endif %{"}"}
                {"{"}% if request.user.groups.all.0.name == 'Broker' %{"}"}
                <li className="nav-item dropdown">
                    <a
                        className="nav-link dropdown-toggle"
                        id="navbarDropdownMenuLinks"
                        role="button"
                        data-toggle="dropdown"
                        aria-haspopup="true"
                        aria-expanded="false"
                        style={{ color: "white" }}
                    >
                        <b style={{ color: "#fff" }}>|</b> &nbsp; Setup
                    </a>
                    <div
                        className="dropdown-menu"
                        aria-labelledby="navbarDropdownMenuLinks"
                    >
                        <a className="dropdown-item" href="/IPOSETUP">
                            IPOs Details
                        </a>
                        <a className="dropdown-item" href="/ClientSetup">
                            Clients Details
                        </a>
                        <a className="dropdown-item" href="/GroupSetup">
                            Groups Details
                        </a>
                        {/* <a class="dropdown-item" href="/PremiumGroupSetup">Premium Trade Group</a> */}
                    </div>
                </li>
                {"{"}% else %{"}"}
                <span className="nav-link ms-2">
                    <b style={{ color: "#fff" }}>|</b> &nbsp; Setup
                </span>
                {"{"}% endif %{"}"}
                {"{"}% if request.user.is_authenticated%{"}"}
                <li className="nav-item active">
                    <a className="nav-link" href="/GroupWiseDashboard">
                        <b>|</b>&nbsp; Group Wise Dashboard
                    </a>
                </li>
                <li className="nav-item active">
                    <a className="nav-link" href="/group-billing-details/">
                        <b>|</b>&nbsp; Positions
                    </a>
                </li>
                <li className="nav-item active">
                    <a className="nav-link" href="/accounting">
                        <b>|</b>&nbsp; Accounting
                    </a>
                </li>
                <li className="nav-item active">
                    <a className="nav-link" href="/trades">
                        <b>|</b>&nbsp; Trades
                    </a>
                </li>
                {"{"}% else %{"}"}
                <span className="nav-link ms-2">
                    <b style={{ color: "#fff" }}>|</b> &nbsp; Group Wise Dashboard
                </span>
                <span className="nav-link ms-2">
                    <b style={{ color: "#fff" }}>|</b> &nbsp; Positions
                </span>
                <span className="nav-link ms-2">
                    <b style={{ color: "#fff" }}>|</b> &nbsp; Trades
                </span>
                <span className="nav-link ms-2">
                    <b style={{ color: "#fff" }}>|</b> &nbsp; Accounting
                </span>
                {"{"}% endif %{"}"}
                {"{"}% if request.user.groups.all.0.name == 'Broker' %{"}"}
                <li className="nav-item active">
                    <a className="nav-link" href="/BackUp">
                        <b>|</b>&nbsp; Backup
                    </a>
                </li>
                {"{"}% else %{"}"}
                <span className="nav-link ms-2">
                    <b style={{ color: "#fff" }}>|</b> &nbsp; Backup
                </span>
                {"{"}% endif %{"}"}
                {"{"}% if request.user.is_authenticated %{"}"}
                <li className="nav-item active">
                    <a className="nav-link" href="/chat" style={{ color: "#ffffff" }}>
                        <b>|</b>&nbsp; WhatsApp Chat
                    </a>
                </li>
                {"{"}% endif %{"}"}
                {"{"}% comment %{"}"}{" "}
                <li className="nav-item active">
                    <a className="nav-link" href="/panalloted">
                        IPO Allotment Analysis
                    </a>
                </li>{" "}
                {"{"}% endcomment %{"}"}
            </ul>
            <ul
                className="navbar-nav ml-auto"
                method="post"
                style={{ marginBottom: 0, marginTop: 2 }}
            >
                <li className="nav-item active"></li>
                {/* <li class="nav-item active">
               <a class="nav-link" data-bs-toggle="modal" data-bs-target="#CreateUser">Create User</a>
              <a class="nav-link" href="/AddCustomerUser"><b>|</b>&nbsp;&nbsp;Create User</a>
          </li> */}
                <li className="nav-item dropdown">
                    {/* href="/" */}
                    <a
                        className="nav-link dropdown-toggle"
                        id="navbarDropdownMenuLink"
                        role="button"
                        data-toggle="dropdown"
                        aria-haspopup="true"
                        aria-expanded="false"
                        style={{ marginBottom: 0, color: "white" }}
                    >
                        <i
                            className="fa fa-user-circle"
                            aria-hidden="true"
                            style={{ fontSize: 18, color: "white" }}
                        />
                        Welcome,
                        {"{"}% comment %{"}"} {"{"}
                        {"{"}request.user {"}"}
                        {"}"} {"{"}% endcomment %{"}"}
                        {"{"}% if not request.user.is_authenticated %{"}"}
                        {"{"}
                        {"{"} request.session.group_name {"}"}
                        {"}"}
                        {"{"}% else %{"}"}
                        {"{"}
                        {"{"} request.user {"}"}
                        {"}"}
                        {"{"}% endif %{"}"}
                    </a>
                    <div
                        className="dropdown-menu user-dropdown"
                        aria-labelledby="navbarDropdownMenuLink"
                    >
                        {"{"}% if request.user.groups.all.0.name == 'Broker' %{"}"}
                        <a className="dropdown-item" href="{% url 'user_profile' %}">
                            User Profile
                        </a>
                        {"{"}% else %{"}"}
                        <span
                            className="dropdown-item"
                            style={{
                                cursor: "default",
                                pointerEvents: "none",
                                opacity: "0.7"
                            }}
                            title="Profile editing is managed by your broker."
                        >
                            User Profile
                        </span>
                        {"{"}% endif %{"}"}
                        {"{"}% comment %{"}"}{" "}
                        <a
                            className="dropdown-item"
                            data-bs-toggle="modal"
                            data-bs-target="#UserProfileModal"
                            style={{ lineHeight: "1.2" }}
                        >
                            User Profile
                        </a>{" "}
                        {"{"}% endcomment %{"}"}
                        <a
                            className="dropdown-item"
                            data-bs-toggle="modal"
                            style={{ lineHeight: "1.2" }}
                        >
                            Expiry Date :{"{"}
                            {"{"}expiry_date {"}"}
                            {"}"}
                        </a>
                        <div style={{ height: 5 }} />
                        {"{"}% if request.user.is_authenticated %{"}"}
                        <a
                            className="dropdown-item"
                            data-bs-toggle="modal"
                            data-bs-target="#Changepassword"
                            style={{ lineHeight: "1.2" }}
                        >
                            Change Password
                        </a>
                        {"{"}% else %{"}"}
                        <span
                            className="dropdown-item"
                            style={{
                                cursor: "default",
                                pointerEvents: "none",
                                opacity: "0.7"
                            }}
                            title="Profile editing is managed by your broker."
                        >
                            Change Password
                        </span>
                        {"{"}%endif%{"}"}
                        <div style={{ height: 5 }} />
                        <a
                            className="dropdown-item"
                            data-bs-toggle="modal"
                            data-bs-target="#logout"
                            style={{ lineHeight: "1.2" }}
                        >
                            <img
                                src="/../static/image/logout.png"
                                width="23px"
                                height="23px"
                                style={{ marginBottom: 5 }}
                            />
                            Logout
                        </a>
                    </div>
                </li>
            </ul>
        </div>
    </nav>
    {/* User Profile Modal */}
    <div
        className="modal fade"
        id="UserProfileModal"
        tabIndex={-1}
        aria-labelledby="UserProfileModalLabel"
        aria-hidden="true"
    >
        <div className="modal-dialog modal-dialog1">
            <div
                className="modal-content chng-box"
                style={{
                    backgroundColor: "whitesmoke",
                    border: "1px solid white",
                    borderRadius: 29
                }}
            >
                <div className="modal-body background">
                    <div
                        className="modal-header"
                        style={{
                            background: "rgb(49, 183, 183)",
                            justifyContent: "center",
                            border: "4px solid rgb(0, 0, 0)",
                            borderTopRightRadius: 22,
                            borderTopLeftRadius: 22,
                            borderBottom: "0px solid white"
                        }}
                    >
                        <b>
                            <h4>
                                {" "}
                                <span
                                    className="modal-title title"
                                    id="UserProfileModalLabel"
                                    style={{ color: "white", padding: "0 1%" }}
                                >
                                    User Profile
                                </span>
                            </h4>
                        </b>
                        <button
                            type="button"
                            className="btn-close"
                            data-bs-dismiss="modal"
                            aria-label="Close"
                            style={{
                                cursor: "pointer",
                                background: "none",
                                border: "none",
                                color: "white",
                                fontSize: 22
                            }}
                        >
                            X
                        </button>
                    </div>
                    <div
                        className="containers"
                        style={{
                            border: "4px solid black",
                            borderBottomLeftRadius: 22,
                            borderBottomRightRadius: 22,
                            padding: "0 15%"
                        }}
                    >
                        <div className="wrapper">
                            <div className="title">
                                <span>
                                    {"{"}
                                    {"{"} request.user {"}"}
                                    {"}"}
                                </span>
                            </div>
                            <form method="post" action="/update-user-profile">
                                {"{"}% csrf_token %{"}"}
                                <div className="row">
                                    <i className="fa fa-user" aria-hidden="true" />
                                    <input
                                        type="text"
                                        name="username"
                                        defaultValue="{{ user.username }}"
                                        readOnly=""
                                    />
                                </div>
                                <div className="row">
                                    <i className="fa fa-envelope" aria-hidden="true" />
                                    <input
                                        type="email"
                                        name="email"
                                        defaultValue="{{ user.email }}"
                                        placeholder="Email"
                                        required=""
                                    />
                                </div>
                                <div className="row">
                                    <i className="fa fa-key" aria-hidden="true" />
                                    <input
                                        type="apppassword"
                                        id="appPassword1"
                                        name="app_password"
                                        placeholder="App Password"
                                        required=""
                                    />
                                    <span
                                        toggle="#appPassword1"
                                        className="fa fa-fw fa-eye field-icon1 toggle-password1"
                                    />
                                </div>
                                {/* <div class="row">
                              <i class="fa fa-key" aria-hidden="true"></i>
                              <input type="password" id="appPassword2" name="confirm_app_password" placeholder="Confirm App Password" required>
                              <span toggle="#appPassword2" class="fa fa-fw fa-eye field-icon2 toggle-password2"></span>
                          </div> */}
                                <br />
                                <div className="row button">
                                    <input
                                        className="btn loginbtn"
                                        type="submit"
                                        defaultValue="Update Profile"
                                    />
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    {/*NEW  Modal FOR Create User MODAL*/}
    <div
        className="modal fade modal1"
        id="CreateUser"
        tabIndex={-1}
        role="dialog"
        aria-labelledby="exampleModalLabel"
        aria-hidden="true"
    >
        <div className="modal-dialog" role="document">
            <div className="modal-content">
                <div
                    className="modal-header"
                    style={{ borderBottom: "1px solid black" }}
                >
                    <b>
                        <h5 className="modal-title" id="exampleModalLabel">
                            Create User
                        </h5>
                    </b>
                    <button
                        type="button"
                        className="close"
                        data-bs-dismiss="modal"
                        aria-label="Close"
                        style={{ fontSize: 20 }}
                    >
                        X
                    </button>
                </div>
                <div className="modal-body">
                    <center>
                        <div className="clearfix">
                            <button
                                type="button"
                                className="btn btn-outline-secondary"
                                style={{ marginRight: 60, width: "25%" }}
                                data-bs-dismiss="modal"
                            >
                                Close
                            </button>
                            <a
                                type="button"
                                className="btn btn-outline-danger"
                                style={{ marginLeft: "-20px", width: "25%" }}
                                href="/logout"
                            >
                                Logout
                            </a>
                        </div>
                    </center>
                </div>
            </div>
        </div>
    </div>
    {/*NEW  Modal FOR logout MODAL*/}
    <div
        className="modal fade modal1"
        id="logout"
        tabIndex={-1}
        role="dialog"
        aria-labelledby="exampleModalLabel"
        aria-hidden="true"
    >
        <div className="modal-dialog">
            <div className="modal-content">
                <div
                    className="modal-header"
                    style={{ borderBottom: "1px solid black" }}
                >
                    <b>
                        <h5 className="modal-title" id="exampleModalLabel">
                            Logout&nbsp;
                            <img
                                src="/../static/image/logout.png"
                                width="23px"
                                height="23px"
                                style={{ marginBottom: 10 }}
                            />
                        </h5>
                    </b>
                    <button
                        type="button"
                        className="close"
                        data-bs-dismiss="modal"
                        aria-label="Close"
                        style={{ fontSize: 20 }}
                    >
                        X
                    </button>
                </div>
                <div className="modal-body">
                    <center>
                        <p>
                            Are you sure you want to logout from {"{"}
                            {"{"} request.user {"}"}
                            {"}"}?
                        </p>
                        <div className="clearfix">
                            <button
                                type="button"
                                className="btn btn-outline-secondary"
                                style={{ marginRight: 60, width: "25%" }}
                                data-bs-dismiss="modal"
                            >
                                Close
                            </button>
                            <a
                                type="button"
                                className="btn btn-outline-danger"
                                style={{ marginLeft: "-20px", width: "25%" }}
                                href="/logout"
                            >
                                Logout
                            </a>
                        </div>
                    </center>
                </div>
            </div>
        </div>
    </div>
    {/* MODAL FOR Changepassword PAGE */}
    {/* Modal */}
    <div
        className="modal fade addipomodal"
        id="Changepassword"
        tabIndex={-1}
        role="dialog"
        aria-labelledby="exampleModalLabel"
        aria-hidden="true"
    >
        <div className="modal-dialog modal-dialog1" role="document">
            <div
                className="modal-content chng-box"
                style={{
                    backgroundColor: "whitesmoke",
                    border: "1px solid white",
                    borderRadius: 29
                }}
            >
                <div className="modal-body background">
                    <div
                        className="modal-header"
                        style={{
                            background: "rgb(49, 183, 183)",
                            alignItem: "center",
                            display: "flex",
                            justifyContent: "space-between",
                            border: "4px solid rgb(0, 0, 0)",
                            borderTopRightRadius: 22,
                            borderTopLeftRadius: 22,
                            borderBottom: "0px solid white"
                        }}
                    >
                        <div style={{ flex: 1, textAlign: "center" }}>
                            <b>
                                <h4>
                                    {" "}
                                    <span
                                        className="modal-title title"
                                        id="staticBackdroLabel"
                                        style={{ color: "white", margin: "0PX" }}
                                    >
                                        Change Password
                                    </span>
                                </h4>
                            </b>
                        </div>
                        <button
                            type="button"
                            className="btn-close"
                            data-bs-dismiss="modal"
                            aria-label="Close"
                            style={{
                                cursor: "pointer",
                                background: "none",
                                border: "none",
                                color: "black",
                                fontSize: 22,
                                fontWeight: 700
                            }}
                        >
                            X
                        </button>
                    </div>
                    <div
                        className="containers"
                        style={{
                            border: "4px solid black",
                            borderBottomLeftRadius: 22,
                            borderBottomRightRadius: 22,
                            padding: "0 15%"
                        }}
                    >
                        <div className="wrapper">
                            <div className="title">
                                <span>
                                    {"{"}
                                    {"{"}request.user {"}"}
                                    {"}"}
                                </span>
                            </div>
                            <form method="post" action="/ChangeUserpassword">
                                {"{"}% csrf_token %{"}"}
                                <div className="row">
                                    <i className="fa fa-lock" aria-hidden="true" />
                                    <input
                                        type="password"
                                        id="inputPassword1"
                                        name="NewPassword"
                                        placeholder="New Password"
                                        required=""
                                    />
                                    <span
                                        toggle="#inputPassword1"
                                        className="fa fa-fw fa-eye field-icon1 toggle-password1"
                                    />
                                </div>
                                <div className="row">
                                    <i className="fa fa-lock" aria-hidden="true" />
                                    <input
                                        type="password"
                                        id="inputPassword2"
                                        name="ConfirmPassword"
                                        placeholder="Confirm Password"
                                        required=""
                                    />
                                    <span
                                        toggle="#inputPassword2"
                                        className="fa fa-fw fa-eye field-icon2 toggle-password2"
                                    />
                                </div>
                                <br />
                                <div className="row button">
                                    <input
                                        className="btn loginbtn"
                                        type="submit"
                                        defaultValue="Submit"
                                    />
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    {/* Optional JavaScript; choose one of the two! */}
    {/* Option 1: Bootstrap Bundle with Popper */}
    {/* Option 2: Separate Popper and Bootstrap JS */}
    {/* Alert MESSAGE CODE AND SCRIPT */}
    {"{"}% comment %{"}"} {"{"}% if messages %{"}"}
    <div
        className="alert alert-danger fixed-top"
        id="success-alert"
        style={{ position: "fixed" }}
    >
        <button type="button" className="close" data-dismiss="alert">
            x
        </button>
        {"{"}% for message in messages %{"}"}
        <strong>
            {"{"}
            {"{"}message{"}"}
            {"}"}
        </strong>
        <br />
        {"{"}% endfor %{"}"}
    </div>
    {"{"}% endif %{"}"} {"{"}% endcomment %{"}"}
    {"{"}% block body %{"}"} {"{"}% endblock %{"}"}
    {/* ======= PWA INSTALL BANNER ======= */}
    <div
        id="pwa-install-banner"
        style={{
            display: "none",
            position: "fixed",
            bottom: 0,
            left: 0,
            right: 0,
            zIndex: 9999,
            background: "linear-gradient(135deg, #2c2c2c 0%, #3a3a3a 100%)",
            color: "white",
            padding: "14px 16px",
            boxShadow: "0 -4px 20px rgba(0,0,0,0.4)",
            borderTop: "2px solid #f0a500",
            fontFamily: "Arial, sans-serif"
        }}
    >
        <div
            style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                maxWidth: 700,
                margin: "0 auto"
            }}
        >
            <img
                src="{% static 'image/pwa_icon_192.png' %}"
                width={44}
                height={44}
                style={{ borderRadius: 10, flexShrink: 0 }}
                alt="IPO Utility Icon"
            />
            <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 700, fontSize: 15, color: "#f0a500" }}>
                    📲 Install IPO Utility
                </div>
                <div
                    id="pwa-banner-msg"
                    style={{ fontSize: 12, color: "#ccc", marginTop: 2 }}
                >
                    Add to your home screen for quick access
                </div>
            </div>
            <div style={{ display: "flex", gap: 8, flexShrink: 0 }}>
                <button
                    id="pwa-install-btn"
                    style={{
                        display: "none",
                        background: "#f0a500",
                        color: "#111",
                        border: "none",
                        padding: "8px 16px",
                        borderRadius: 20,
                        fontWeight: 700,
                        cursor: "pointer",
                        fontSize: 13,
                        whiteSpace: "nowrap"
                    }}
                >
                    ⬇ Install
                </button>
                <button
                    id="pwa-dismiss-btn"
                    style={{
                        background: "transparent",
                        color: "#aaa",
                        border: "1px solid #555",
                        padding: "8px 12px",
                        borderRadius: 20,
                        cursor: "pointer",
                        fontSize: 13,
                        whiteSpace: "nowrap"
                    }}
                >
                    ✕ Close
                </button>
            </div>
        </div>
        {/* iOS instructions panel (hidden by default) */}
        <div
            id="pwa-ios-instructions"
            style={{
                display: "none",
                maxWidth: 700,
                margin: "10px auto 0",
                background: "#444",
                borderRadius: 10,
                padding: "10px 14px",
                fontSize: 12,
                color: "#eee",
                lineHeight: "1.7"
            }}
        >
            <b style={{ color: "#f0a500" }}>How to install on iPhone / iPad:</b>
            <br />
            1. Tap the <b>Share</b> button <span style={{ fontSize: 16 }}>⬆</span> in
            Safari's toolbar
            <br />
            2. Scroll down and tap <b>"Add to Home Screen"</b>{" "}
            <span style={{ fontSize: 14 }}>➕</span>
            <br />
            3. Tap <b>Add</b> in the top-right corner
        </div>
    </div>
    {/* ======= END PWA INSTALL BANNER ======= */}
</>

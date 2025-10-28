import QtQuick 2.14
import QtQuick.Controls 2.14
import QtQuick.Layouts 1.14
import QtGraphicalEffects 1.14
import QtQuick.Window 2.2
import "./PK" 1.0 as PK
import PK.Models 1.0
import "js/Global.js" as Global


Page {

    id: root
    width: 800
    height: 600

    signal done
    signal sentResetEmail
    signal sentResetEmailFailed
    signal purchasedLicense
    signal purchaseLicenseFailed
    signal canceledLicense
    signal cancelLicenseFailed
    signal userUpdated // testing
    signal licenseActivated(string code)
    signal licenseActivationFailed
    signal licenseDeactivated(string code)
    signal licenseDeactivationFailed
    signal licenseImported
    signal licenseImportFailed
    signal authStateChanged(string state) // testing

    property var user: (function(hash) {
        if(session.loggedIn)
            return session.userDict
        else
            return null
    }(session.hash))

    property var publicPolicies: []
    property var userLicenses: null
    property var activeFeatures: []
    property var purchasingPolicy: null
    property var purchaseButtons: [] // testing
    property bool _activatingLicense: false

    property var greenColor: util.IS_UI_DARK_MODE ? '#801aa260' : '#8056d366'
    property var redColor: util.IS_UI_DARK_MODE ? '#80ff0000' : '#80e8564e'

    Timer {
        id: hackTimer
        interval: 0
        repeat: false
        onTriggered:  slideView.updateSlideX()
    }
    onWidthChanged: hackTimer.start() // Bug in SwipView or something causing incomplete updates

    function debug(s) {
        // print(s)
    }

    Component.onCompleted: root.updateFromSession()

    // for tests only
    Component.onDestruction: Global.deinit()

    /////////////////////////////////////////////////
    //
    //  Verbs
    //
    /////////////////////////////////////////////////

    Connections {
        target: root

        function onSentResetEmail() {
            util.informationBox('Sent email', util.S_EMAIL_SENT_TO_CHANGE_PASSWORD)
        }

        function onSentResetEmailFailed() {
            util.criticalBox('Server error', util.S_FAILED_TO_SEND_PASSWORD_RESET_EMAIL)
        }
    }

    Connections {
        target: session

        function onChanged() {
            root.updateFromSession()
        }
        function onLoginFailed() {
            authErrorMessage.text = 'Login failed'
            authPage.enabled = true
        }

        function onLogoutFailed() {
            authPage.enabled = true
        }
    }

    function updateFromSession() {

        if(session.activeFeatures()) {
            root.activeFeatures = session.activeFeatures()
        } else {
            root.activeFeatures = []
        }

        //
        // Licenses
        //

        function mockActivation() {
            return {
                machine: {
                    code: 'f2171278-e3a6-4a72-826a-ccb21209138e',
                    name: '<AVAILABLE>',
                },
                updated_at: null,
                _mock: true
            }
        }

        var sessionData = session.data()

        // 1. Called on init when MainWindow pulls it from AppConfig.
        // 2. Retrieves. 
        var userLicenses = (sessionData && sessionData.session && sessionData.session.user) ? sessionData.session.user.licenses : []

        // add all placeholder activations
        for(var i=0; i < userLicenses.length; i++) {
            var license = userLicenses[i];
            for(var j=license.activations.length; j < license.policy.maxActivations; j++) {
                license.activations.push(mockActivation());
            }
        }

        var grouped = { active: [], inactive: [], expired: [], mock: [] };
        for(var i=0; i < userLicenses.length; i++) {
            var x = userLicenses[i];
            if(x._mock) { grouped.mock.push(x); continue }
            if(x.active) { grouped.active.push(x); continue }
            if(!x.active && !x.expired) { grouped.inactive.push(x); continue }
            if(x.expired) { grouped.expired.push(x); continue }
        }
        userLicenses = grouped.active.concat(grouped.inactive).concat(grouped.mock).concat(grouped.expired)
        root.userLicenses = null
        root.userLicenses = userLicenses
        root.publicPolicies = null
        root.publicPolicies = (sessionData && sessionData.policies) ? sessionData.policies : null

        //
        // UI
        //

        if(session.loggedIn) {

            var sessionData = session.data()
            var user = sessionData.session.user

            if((user && user.licenses.length > 0) || util.IS_IOS) { // can't sell anything on iOS
                slideView.currentIndex = 2
            } else {
                slideView.currentIndex = 1
            }
            authPage.enabled = true
            creditCardForm.submitting = false // why not?
            var args = {
                session: session.token,
            }
            // first get name from account
            Global.server(util, session, 'GET', '/machines/' + util.HARDWARE_UUID, args, function(response) {
                if(response.status_code === 200) {
                    machineNameField.text = response.data.name
                } else if(response.status_code == 404) {
                    var args = {
                        session: session.token,
                        name: util.MACHINE_NAME
                    }
                    // create if doesn't exist
                    Global.server(util, session, 'POST', '/machines/' + util.HARDWARE_UUID, args, function(response) {
                        if(response.status_code === 200) {
                            machineNameField.text = util.MACHINE_NAME
                        } else {
                            debug("Error creating machine entry on server.")
                        }
                    })
                }
            })

        } else {

            // Logged out

            slideView.currentIndex = 0
            authPage.enabled = true
            authForm.reset()
        }        
    }

    function cancelLicense(license) {
        var yes = util.questionBox('Are you sure?',
                                   'Are you sure you want to cancel this subscription? You may continue to use the license until it expires.')
        if(yes) {
            var args = {
                session: session.token,
                key: license.key
            }
            Global.server(util, session, 'POST', '/licenses/' + license.key + '/cancel', args, function(response) {
                if(response.status_code === 200) {
                    root.canceledLicense()
                    session.update()
                } else {
                    util.criticalBox('Server error', response.user_message)
                    root.cancelLicenseFailed()
                }
            })
        }
    }

    function activateLicense(license) {
        for(var i=0; i < license.activations.length; i++) {
            var activation = license.activations[i];
            if(activation.machine === util.HARDWARE_UUID) {
                util.informationBox('License already activated',
                                    'This license is already activated for this machine')
                return
            }
        }
        var args = {
            session: session.token,
            license: license.key,
            machine: util.HARDWARE_UUID,
            name: machineNameField.text
        }
        root._activatingLicense = true
        Global.server(util, session, 'POST', '/activations', args, function(response) {
            root._activatingLicense = false
            if(response.status_code === 200) {
                root.licenseActivated(license.code)
                session.update()
            } else {
                util.informationBox('Activation failed', 'Failed to activate license on this device')
                root.licenseActivationFailed()
            }
        })
    }

    function deactivateLicense(license, activation) {
        var args = {
            session: session.token,
            license: license.key,
            machine: activation.machine.code
        }
        root._activatingLicense = true
        Global.server(util, session, 'DELETE', '/activations/' + activation.id, args, function(response) {
            root._activatingLicense = false
            if(response.status_code === 200) {
                root.licenseDeactivated(license.code)
                session.update()
            } else {
                util.criticalBox('Server error', 'Failed to deactivate license on this device')
                root.licenseDeactivationFailed()
            }
        })
    }

    function purchaseLicense(policy) {
        if(policy) {
            root.purchasingPolicy = policy
        } else {
            root.purchasingPolicy = null
        }
        if(slideView.currentIndex != 1) {
            authForm.clear()
            ccNumField.forceActiveFocus()
            slideView.currentIndex = 1
        }
    }

    function onVerbCantReachServer() {
        // Careful that this is only called once per user click/return-press.
        util.informationBox("Can't reach server", "Could not reach the server. Check that your internet connection is working, otherwise the server may be down which requires contacting support.")
    }

    /////////////////////////////////////////////////
    //
    //  Items
    //
    /////////////////////////////////////////////////


    Rectangle {

        id: slideView
        objectName: 'slideView'
        color: util.QML_WINDOW_BG
        width: root.width
        height: root.height
        property int currentIndex: 0

        onCurrentIndexChanged: {
            if(currentIndex == 0)
                show0Animation.start()
            else if(currentIndex == 1)
                show1Animation.start()
            else if(currentIndex == 2)
                show2Animation.start()
        }

        function updateSlideX() {
            stage.x = -(width * currentIndex)
        }

        PropertyAnimation {
            id: show0Animation; target: stage; property: 'x'; duration: util.ANIM_DURATION_MS; easing.type: Easing.InOutQuad
            from: stage.x
            to: 0
        }
        PropertyAnimation {
            id: show1Animation; target: stage; property: 'x'; duration: util.ANIM_DURATION_MS; easing.type: Easing.InOutQuad
            from: stage.x
            to: -slideView.width
        }
        PropertyAnimation {
            id: show2Animation; target: stage; property: 'x'; duration: util.ANIM_DURATION_MS; easing.type: Easing.InOutQuad
            from: stage.x
            to: -(slideView.width * 2)
        }


        Rectangle {

            id: stage
            width: slideView.width * 3
            height: slideView.height
            color: util.QML_WINDOW_BG


            /////////////////////////////////////////////////
            //
            //  Auth Page
            //
            /////////////////////////////////////////////////


            Flickable {

                id: authPage
                width: root.width
                height: root.height
                // color: util.QML_WINDOW_BG
                contentX: 0
                contentHeight: authLayout.height + 100
                contentWidth: width - (util.QML_MARGINS * 2)
                leftMargin: util.QML_MARGINS
                rightMargin: util.QML_MARGINS

                ColumnLayout {

                    id: authLayout
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: util.QML_MARGINS                    

                    PK.Label {
                        id: authPageTitle
                        wrapMode: Text.WordWrap              
                        Layout.topMargin: 50
                        Layout.alignment: Qt.AlignHCenter
                        Layout.maximumWidth: parent.width
                        width: 250
                        font {
                            pixelSize: 32
                            family: util.FONT_FAMILY
                        }
                        text: {
                            if(authForm.state == 'email')
                                'Enter email'
                            else if(authForm.state == 'code')
                                'Enter confirmation code'
                            else if(authForm.state == 'password')
                                'Log in'
                            else if(authForm.state == 'update')
                                'Set Password and log in'
                        }
                    }

                    PK.Label {
                        id: authInstructions
                        Layout.topMargin: util.QML_MARGINS
                        Layout.alignment: Qt.AlignHCenter
                        Layout.maximumWidth: parent.width
                        wrapMode: Text.WordWrap
                        visible: authForm.state != 'update'
                        font {
                            pixelSize: 12
                            family: util.FONT_FAMILY
                        }
                        text: {
                            if(authForm.state == 'email')
                                'You must log in or create an account to use family diagram.'
                            else if(authForm.state == 'code')
                                'Enter the confirmation code sent to you in an email in the box below.'
                            else if(authForm.state == 'password')
                                ''
                            else if(authForm.state == 'update')
                                ''
                        }
                    }

                    ColumnLayout {

                        id: authForm
                        objectName: 'authForm'
                        state: 'email' // ('email', 'password', 'code', 'update')
                        property int entered_user_id: -1
                        Layout.topMargin: 0
                        Layout.alignment: Qt.AlignHCenter
                        Layout.minimumWidth: 350
                        Keys.onReturnPressed: authForm.submit()
                        Keys.onEnterPressed: authForm.submit()
                        function setState(x) {
                            state = x
                            root.authStateChanged(x) // testing
                        }

                        function clear() {
                            ccNumField.text = ''
                            ccExpMonthField.text = ''
                            ccExpYearField.text = ''
                            ccCVCField.text = ''
                            // ccZipField.text = ''
                        }

                        // Email

                        PK.Label {
                            text: 'Email:'
                            width: authUsernameField.width
                            Layout.alignment: Qt.AlignHCenter
                            Layout.minimumWidth: authUsernameField.width
                        }

                        PK.TextField {
                            id: authUsernameField
                            objectName: 'authUsernameField'
                            readOnly: authForm.state != 'email'
                            validator: RegExpValidator { regExp:/\w+([-+.']\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*/ }
                            palette.base: acceptableInput && !readOnly ? greenColor : defaultBackgroundColor
                            Layout.alignment: Qt.AlignHCenter
                            Layout.fillWidth: true
                            KeyNavigation.tab: {
                                if(authForm.state == 'email')
                                    authSubmitButton
                                else if(authForm.state == 'code')
                                    authCodeField
                                else if(authForm.state == 'update')
                                    authFirstNameField
                                else if(authForm.state == 'password')
                                    authPasswordField
                            }
                        }

                        // Code

                        PK.Label {
                            text: 'Enter code:'
                            visible: authForm.state == 'code'
                        }

                        PK.TextField {
                            id: authCodeField
                            objectName: 'authCodeField'
                            echoMode: TextInput.Password
                            visible: authForm.state == 'code'
                            Layout.alignment: Qt.AlignHCenter
                            Layout.fillWidth: true
                            KeyNavigation.tab: authCancelButton
                        }

                        // Password

                        PK.Label {
                            text: 'Password'
                            visible: authForm.state == 'password'
                        }

                        PK.TextField {
                            id: authPasswordField
                            objectName: 'authPasswordField'
                            echoMode: TextInput.Password
                            visible: authForm.state == 'password'
                            Layout.fillWidth: true
                            KeyNavigation.tab: authCancelButton
                        }

                        PK.Label {
                            id: authResetPasswordLink
                            objectName: 'authResetPasswordLink'
                            text: 'Reset Password'
                            visible: authForm.state == 'password'
                            Layout.topMargin: 5
                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    authForm.enabled = false
                                    var args = { username: authUsernameField.text }
                                    Global.server(util, session, 'POST', '/users/' + authForm.entered_user_id + '/email_code', args, function(response) {
                                        if(response.status_code === 200) {
                                            root.sentResetEmail()
                                            authForm.setState('code')
                                        } else {
                                            root.sentResetEmailFailed()
                                        }
                                        authForm.enabled = true
                                    })
                                }
                            }
                        }

                        // Update User

                        PK.Label {
                            text: 'First Name *'
                            visible: authForm.state == 'update'
                        }

                        PK.TextField {
                            id: authFirstNameField
                            objectName: 'authFirstNameField'
                            visible: authForm.state == 'update'
                            // property bool valid: text !== ''
                            // palette.base: valid ? greenColor : defaultBackgroundColor
                            Layout.fillWidth: true
                            KeyNavigation.tab: authLastNameField
                        }

                        PK.Label {
                            text: 'Last Name *'
                            visible: authForm.state == 'update'
                        }

                        PK.TextField {
                            id: authLastNameField
                            objectName: 'authLastNameField'
                            visible: authForm.state == 'update'
                            // property bool valid: text !== ''
                            // palette.base: valid ? greenColor : defaultBackgroundColor
                            Layout.fillWidth: true
                            KeyNavigation.tab: authNewPasswordField
                        }
                        
                        PK.Label {
                            text: 'New Password'
                            visible: authForm.state == 'update'
                        }

                        PK.TextField {
                            id: authNewPasswordField
                            objectName: 'authNewPasswordField'
                            echoMode: TextInput.Password
                            visible: authForm.state == 'update'
                            Layout.fillWidth: true
                            KeyNavigation.tab: authConfirmPasswordField
                        }

                        PK.Label {
                            text: 'Confirm Password'
                            visible: authForm.state == 'update'
                        }

                        PK.TextField {
                            id: authConfirmPasswordField
                            objectName: 'authConfirmPasswordField'
                            echoMode: TextInput.Password
                            visible: authForm.state == 'update'
                            KeyNavigation.tab: authCancelButton
                            Layout.fillWidth: true
                        }

                        PK.Label {
                            id: authErrorMessage
                            wrapMode: Text.WordWrap
                            color: redColor
                            visible: text != ''
                            Layout.maximumWidth: 250
                        }

                        RowLayout {

                            Layout.topMargin: util.QML_MARGINS

                            /* PK.CheckBox { */
                            /*     id: loginOrRegisterBox */
                            /*     objectName: 'loginOrRegisterBox' */
                            /*     text: 'I already have an account' */
                            /*     Layout.alignment: Qt.AlignHCenter */
                            /*     KeyNavigation.tab: authButton */
                            /*     onCheckedChanged: { */
                            /*         authUsernameField.text = '' */
                            /*         passwordField.text = '' */
                            /*         confirmPasswordField.text = '' */
                            /*         authErrorMessage.text = '' */
                            /*     } */
                            /* } */
                            PK.Button {
                                id: authCancelButton
                                text: 'Cancel'
                                visible: authForm.state == 'code' || authForm.state == 'password'
                                KeyNavigation.tab: authResendCodeButton
                                onClicked: authForm.reset()
                            }
                            PK.Button {
                                id: authResendCodeButton
                                objectName: 'authResendCodeButton'
                                text: 'Resend'
                                visible: authForm.state == 'code'
                                KeyNavigation.tab: authSubmitButton
                                onClicked: {
                                    authForm.enabled = false
                                    Global.server(util, session, 'POST', '/users/' + authForm.entered_user_id + '/email_code', null, function(response) {
                                        debug('HTTP: /users/' + authForm.entered_user_id + '/email_code :: ' + response.status_code)
                                        if(response.status_code === 200) {
                                            root.sentResetEmail()
                                            authForm.setState('code')
                                        } else {
                                            root.sentResetEmailFailed()
                                        }
                                        authForm.enabled = true
                                    })
                                }
                            }
                            Rectangle {
                                Layout.fillWidth: true
                                color: 'transparent'
                            }
                            PK.Button {
                                id: authSubmitButton
                                objectName: 'authSubmitButton'
                                defaultBackgroundColor: '#1d63f9'
                                textColor: 'white'
                                text: {
                                    if(authForm.state == 'email')
                                        'Next'
                                    else if(authForm.state == 'code') 
                                        'Next'
                                    else if(authForm.state == 'password')
                                        'Login'
                                    else if(authForm.state == 'update')
                                        'Save'
                                }
                                Layout.alignment: Qt.AlignRight
                                KeyNavigation.tab: authUsernameField
                                onClicked: authForm.submit()
                            }
                        }
                        function reset() {
                            authErrorMessage.text = ''
                            authUsernameField.text = ''
                            authPasswordField.text = ''
                            authNewPasswordField.text = ''
                            authConfirmPasswordField.text = ''
                            authCodeField.text = ''
                            authForm.enabled = true
                            entered_user_id = -1
                            setState('email')
                        }
                        function submit() {
                            var args
                            authErrorMessage.text = ''
                            if(authForm.state == 'email') {
                                authForm.entered_user_id = -1
                                args = {
                                    username: authUsernameField.text
                                }
                                authForm.enabled = false
                                Global.server(util, session, 'POST', '/users/status', args, function(response) {
                                    debug('HTTP: /users/status :: ' + response.status_code, response.data ? response.data.status : '')
                                    authForm.enabled = true
                                    if(response.status_code === 200) {
                                        if(response.data.status == 'confirmed') {
                                            authForm.entered_user_id = response.data.id
                                            authForm.setState('password')
                                            authPasswordField.forceActiveFocus()
                                        } else if(response.data.status == 'pending') {
                                            authForm.entered_user_id = response.data.id
                                            authForm.setState('code')
                                            authCodeField.forceActiveFocus()
                                        } else if(response.data.status == 'not found') {

                                            authForm.enabled = false
                                            Global.server(util, session, 'POST', '/users', args, function(response) {
                                                debug('HTTP: /users :: ' + response.status_code)
                                                authForm.enabled = true
                                                if(response.status_code === 200) {

                                                    authForm.entered_user_id = response.data.id
                                                    authForm.enabled = false
                                                    Global.server(util, session, 'POST', '/users/' + authForm.entered_user_id + '/email_code', args, function(response) {
                                                        debug('HTTP: /users/' + authForm.entered_user_id + '/email_code :: ' + response.status_code)
                                                        authForm.enabled = true
                                                        if(response.status_code === 200) {
                                                            root.sentResetEmail()
                                                            authForm.setState('code')
                                                            authCodeField.forceActiveFocus()
                                                        } else {
                                                            root.sentResetEmailFailed()
                                                        }
                                                    })
                                                }
                                            })
                                        }
                                    } else if(response.status_code >= 500 && response.status_code < 600) {
                                        util.criticalBox('Server internal error', 'The server crashed while processing your request (HTTP ' + response.status_code + ').\n\nContact support and/or try again later.')
                                    } else if(response.status_code == 0) {
                                        root.onVerbCantReachServer()
                                    } else {
                                        util.criticalBox('Server error', 'The server An error occurred checking the user status (HTTP ' + response.status_code + ').\n\nPlease try again later.')
                                    }
                                })
                            } else if(authForm.state == 'code') {
                                args = {
                                    reset_password_code: authCodeField.text
                                }
                                authForm.enabled = false
                                Global.server(util, session, 'POST', '/users/' + authForm.entered_user_id + '/confirm', args, function(response) {
                                    debug('HTTP: /users :: ' + response.status_code)
                                    authForm.enabled = true
                                    if(response.status_code === 200) {
                                        authFirstNameField.text = response.data.first_name
                                        authLastNameField.text = response.data.last_name
                                        authForm.setState('update')
                                    } else if(response.status_code == 401) {
                                        util.informationBox('Incorrect code', 'That code is incorrect. Please try again.')
                                    }
                                })
                            } else if(authForm.state == 'update') {

                                if(! session.loggedIn) {
                                    // creating user, so passwords are required
                                    if(! authNewPasswordField.text || !authConfirmPasswordField.text) {
                                        util.informationBox("Passwords are required", "The password fields are required.")
                                        return
                                    }
                                }

                                if(authNewPasswordField.text != authConfirmPasswordField.text) {
                                    util.informationBox("Passwords don't match", "The password fields do not match. Leave them blank if you do not wish to change your password.")
                                    return
                                }
                                if(!authFirstNameField.text || ! authLastNameField.text) {
                                    util.informationBox("Fill out required fields", "Both the first an  d last name fields are required.")
                                    return
                                }
                                args = {
                                    username: authUsernameField.text,
                                    password: authNewPasswordField.text,
                                    confirmPassword: authConfirmPasswordField.text,
                                    first_name: authFirstNameField.text,
                                    last_name: authLastNameField.text
                                }
                                if(session.loggedIn) {
                                    args.session = session.token
                                } else {
                                    args.reset_password_code = authCodeField.text
                                }
                                authForm.enabled = false
                                Global.server(util, session, 'POST', '/users/' + authForm.entered_user_id, args, function(response) {
                                    debug('POST: /users/' + authForm.entered_user_id + ' :: ' + response.status_code)
                                    authForm.enabled = true
                                    if(response.status_code === 200) {
                                        authForm.entered_user_id = -1
                                        if(session.loggedIn) {
                                            session.update()
                                            slideView.currentIndex = 2
                                            authForm.reset()
                                            root.userUpdated() // testing
                                        } else {
                                            authForm.enabled = false
                                            session.login(authUsernameField.text, authNewPasswordField.text)
                                        }
                                    }
                                })
                            } else if(authForm.state == 'password') {
                                args = {
                                    username: authUsernameField.text,
                                    password: authPasswordField.text
                                }
                                authForm.enabled = false
                                session.login(authUsernameField.text, authPasswordField.text)
                            }
                        }
                    }
                }
            }


            /////////////////////////////////////////////////
            //
            //  Cart Page
            //
            /////////////////////////////////////////////////


            Flickable {
                id: cartPage
                x: root.width
                width: root.width
                height: root.height
                contentX: 0
                contentHeight: cartLayout.height + 100
                clip: true

                MouseArea {
                    anchors.fill: parent
                    propagateComposedEvents: true
                    onClicked: {
                        if(root.purchasingPolicy != null) {
                            cartPage.cancelPurchase()
                        } else {
                            // choose prev|next policy b/c SwipeArea isn't very flexible.
                            var swipeViewPos = cartPoliciesRow.mapFromItem(cartPoliciesRow, cartPoliciesRow.x, cartPoliciesRow.y)
                            if(mouse.y >= swipeViewPos.y && mouse.y <= (swipeViewPos.y + cartPoliciesRow.height)) {
                                if(mouse.x < swipeViewPos.x) {
                                    if(cartPoliciesRow.currentIndex > 0) {
                                        cartPoliciesRow.currentIndex -= 1
                                    }
                                } else if(mouse.x > (swipeViewPos.x + cartPoliciesRow.width)) {
                                    if(cartPoliciesRow.currentIndex < cartPoliciesRow.count) {
                                        cartPoliciesRow.currentIndex += 1
                                    }
                                }
                            }
                        }
                    }
                }

                function cancelPurchase() {
                    root.purchasingPolicy = null
                    authForm.clear()
                    cartPage.scrollToTop()
                }

                function scrollToTop() {
                    cartScrollToBottomAnim.from = cartPage.contentY
                    cartScrollToBottomAnim.to = 0
                    cartScrollToBottomAnim.start()
                }
                function scrollToBottom() {
                    cartScrollToBottomAnim.from = cartPage.contentY
                    cartScrollToBottomAnim.to = cartPage.contentHeight - cartPage.height
                    cartScrollToBottomAnim.start()
                }

                PropertyAnimation {
                    id: cartScrollToBottomAnim
                    target: cartPage; property: 'contentY'; duration: util.ANIM_DURATION_MS; easing.type: Easing.InOutQuad;
                }

                ColumnLayout {
                    id: cartLayout
                    width: cartPage.width // - (util.QML_MARGINS * 2)
                    // topPadding: util.QML_MARGINS
                    // bottomPadding: util.QML_MARGINS
                    //spacing: util.QML_MARGINS

                    SwipeView {
                        id: cartPoliciesRow
                        property int cardWidth: 150
                        property int nCards: root.publicPolicies ? root.publicPolicies.length : 0
                        z: 2
                        width: cardWidth + (util.QML_MARGINS * 4) // parent.width // see hack below in onItemAdded()
                        height: 290
                        Layout.alignment: Qt.AlignHCenter

                        Repeater {
                            id: publicPoliciesRepeater
                            model: root.publicPolicies

                            delegate: Rectangle {

                                property var dPolicy: root.publicPolicies[index]
                                color: 'transparent'

                                Rectangle {

                                    id: dRoot
                                    property var dropShadow: null
                                    objectName: 'publicPolicyDelegate_' + index
                                    width: 190
                                    height: 250
                                    anchors.centerIn: parent
                                    color: util.QML_HEADER_BG
                                    border {
                                        width: 1
                                        color: util.QML_ITEM_BORDER_COLOR
                                    }
                                    opacity: (!root.purchasingPolicy || root.purchasingPolicy === dPolicy) ? 1.0 : .3 
                                    scale: {
                                        if(!root.purchasingPolicy)
                                            1.0
                                        else if(root.purchasingPolicy === dPolicy)
                                            1.15
                                        else
                                            .9
                                    }
                                    Behavior on opacity {
                                        NumberAnimation { duration: util.ANIM_DURATION_MS; easing.type: Easing.InOutQuad }
                                    }
                                    Behavior on scale {
                                        NumberAnimation { duration: util.ANIM_DURATION_MS; easing.type: Easing.InOutQuad }
                                    }

                                    Column {
                                        width: parent.width
                                        topPadding: 25
                                        rightPadding: 15
                                        leftPadding: 15
                                        bottomPadding: 15
                                        property int pkSpacing: 15
                                        PK.Label {
                                            text: dPolicy.name
                                            width: dRoot.width - util.QML_MARGINS
                                            font {
                                                pixelSize: 14
                                                family: util.FONT_FAMILY
                                            }
                                            horizontalAlignment: Text.AlignHCenter
                                            wrapMode: Text.WordWrap
                                            anchors.horizontalCenter: parent.horizontalCenter
                                        }
                                        Rectangle {
                                            width: 1
                                            height: parent.pkSpacing
                                            color: 'transparent'
                                        }
                                        PK.Label {
                                            text: dPolicy.amount + ' USD'
                                            font.pixelSize: 20
                                            anchors.horizontalCenter: parent.horizontalCenter
                                        }
                                        Rectangle {
                                            width: 1
                                            height: parent.pkSpacing
                                            color: 'transparent'
                                        }
                                        PK.Label {
                                            text: 'Maximum <b>' + dPolicy.maxActivations + '</b> Devices' //+ ', Term: ' + dPolicy.days_valid
                                            anchors.horizontalCenter: parent.horizontalCenter
                                        }
                                        Rectangle {
                                            width: parent.pkSpacing
                                            height: 5
                                            color: 'transparent'
                                        }
                                        PK.Label {
                                            text: dPolicy.description ? dPolicy.description : ''
                                            width: dRoot.width - util.QML_MARGINS
                                            height: 45
                                            maximumLineCount: 3
                                            elide: Text.ElideLeft
                                            wrapMode: Text.WordWrap
                                            horizontalAlignment: Text.AlignHCenter
                                            anchors.horizontalCenter: parent.horizontalCenter
                                        }
                                        Rectangle {
                                            width: 1
                                            height: parent.pkSpacing + 5
                                            color: 'transparent'
                                        }
                                        PK.Button {
                                            text: 'Purchase'
                                            enabled: dPolicy.active
                                            anchors.horizontalCenter: parent.horizontalCenter
                                            background: Rectangle { color: greenColor }
                                            onClicked: {
                                                root.purchaseLicense(dPolicy)
                                                cartPage.scrollToBottom()
                                            }

                                            // testing
                                            Component.onCompleted: root.purchaseButtons.push(this)
                                            Component.onDestruction: Global.arrayRemove(root.purchaseButtons, this)
                                        }
                                    }
                                    PK.Label {
                                        text: 'Coming Soon'
                                        padding: 8
                                        font.pixelSize: 18
                                        visible: !dPolicy.active && dPolicy['public']
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        anchors.bottom: parent.bottom
                                        anchors.bottomMargin: -5
                                        background: Rectangle { color: redColor }
                                        transform: Rotation { origin.x: 0; origin.y: 0; angle: -20}
                                    }
                                }
                            }
                            onItemAdded: function(index, item) {
                                if(index == root.publicPolicies.length - 1) {
                                    // finished loading
                                    cartPoliciesRow.currentIndex = 1
                                }
                                // cartPoliciesRow.width = Qt.binding(function() { return root.width }) // hack: binding is lost somehow
//                               item.dropShadow = shadowDelegate.createObject(cartPage, { source: item })
                            }
                            onItemRemoved: function(index, item) {
                               //item.dropShadow.destroy()
                            }
                        }
                     
                    }

                    Component {
                        id: shadowDelegate
                        DropShadow {
                            x: source.x + cartPoliciesRow.x
                            y: source.y + cartPoliciesRow.y
                            scale: source.scale
                            z: 1
                            width: source.width
                            height: source.height
                            horizontalOffset: 3 * source.scale
                            verticalOffset: 3 * source.scale
                            radius: 8.0
                            samples: 17
                            color: "#80000000"
                            source: publicPoliciesRepeater.itemAt(index)
                        }
                    }

                    Column {
                        enabled: ! root.purchasingPolicy
                        Layout.margins: util.QML_MARGINS
                        Layout.alignment: Qt.AlignHCenter
                        
                        opacity: ! root.purchasingPolicy ? 1 : 0
                        Behavior on opacity {
                            NumberAnimation { duration: util.ANIM_DURATION_MS; easing.type: Easing.InOutQuad }
                        }
                        
                        PK.Label {
                            text: 'Or'
                            font.pixelSize: 18
                            bottomPadding: 35
                            width: parent.width
                            horizontalAlignment: Text.AlignHCenter
                        }

                        ColumnLayout {
                            PK.Label {
                                text: 'Add license by key:'
                                font {
                                    family: util.FONT_FAMILY
                                    pixelSize: 18
                                }
                                Layout.fillWidth: true
                                Layout.bottomMargin: 5
                                horizontalAlignment: Text.AlignHCenter
                            }
                            PK.TextField {
                                id: addLicenseKeyField
                                objectName: 'addLicenseKeyField'
                                Layout.minimumWidth: 250
                                placeholderText: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
                                // inputMask: 'HHHHHHHH-HHHH-HHHH-HHHH-HHHHHHHHHHHH'
                                property bool valid: isValid(text)
                                color: enabled ? (valid ? greenColor : util.QML_ACTIVE_TEXT_COLOR) : util.QML_INACTIVE_TEXT_COLOR
                                function isValid(_text) {
                                    var pattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
                                    return pattern.test(addLicenseKeyField.text)
                                }
                                Keys.onReturnPressed: submitAddLicenseKey()
                                Keys.onEnterPressed: submitAddLicenseKey()
                                function submitAddLicenseKey() {
                                    if(!valid)
                                        return
                                    var uuid = addLicenseKeyField.text
                                    var args = {
                                        session: session.token,
                                        key: uuid,
                                        machine: {
                                            code: util.HARDWARE_UUID,
                                            name: machineNameField.text
                                        }
                                    }
                                    Global.server(util, session, 'POST', '/licenses/' + uuid + '/import', args, function(response) {
                                        if(response.status_code === 200) {
                                            addLicenseKeyField.text = ''
                                            slideView.currentIndex = 2

                                            util.informationBox('License imported', 'The license was added to your account')
                                            if(root.user && root.user.licenses.length == 0) {
                                                // first license purchase, hide dialog
                                                root.done()
                                            } else {
                                                slideView.currentIndex = 2
                                            }
                                            root.licenseImported()
                                            session.update()
                                        } else {
                                            util.criticalBox('Server error', 'Failed to import license on this device')
                                            root.licenseImportFailed()
                                        }
                                    })
                                }
                            }   
                        }
                    }
                }

                ColumnLayout {

                    id: creditCardForm
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: 80
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: util.QML_MARGINS / 2
                    enabled: ! submitting
                    property bool submitting: false
                    property bool acceptableInput: ccNumField.text && ccExpMonthField.acceptableInput && ccExpYearField.acceptableInput && ccCVCField.acceptableInput //&& ccZipField.acceptableInput
                    // property var salesTaxRate: util.salesTaxRate(ccZipField.text)
                    // property var salesTax: (salesTaxRate > -1 && root.purchasingPolicy) ? salesTaxRate * root.purchasingPolicy.amount : 0
                    // property var ccServiceChargeRate: .029
                    // property var ccServiceCharge: root.purchasingPolicy ? root.purchasingPolicy.amount * ccServiceChargeRate : 0
                    // property var saleTotal: root.purchasingPolicy ? (root.purchasingPolicy.amount + salesTax + ccServiceCharge).toFixed(2): -1
                    property var saleTotal: root.purchasingPolicy ? root.purchasingPolicy.amount : -1
                    transform: Translate {
                        y: root.purchasingPolicy !== null ? 0 : creditCardForm.y * 2
                        Behavior on y {
                            NumberAnimation { duration: util.ANIM_DURATION_MS; easing.type: Easing.InOutQuad }
                        }
                    }
                    Layout.margins: util.QML_MARGINS
                    
                    PK.Label {
                        width: parent.width
                        text: root.purchasingPolicy ? 'Purchasing: ' + root.purchasingPolicy.name + ' (' + root.purchasingPolicy.amount + ' USD)' : ''
                        property var taxString: creditCardForm.salesTaxRate > -1 ? ' + ' + parseInt(creditCardForm.salesTaxRate*100) + '% tax' : ''
                        // text: root.purchasingPolicy ? 'Purchasing: ' + root.purchasingPolicy.name + ' (' + root.purchasingPolicy.amount + ' USD' + taxString + ' + ' + (creditCardForm.ccServiceChargeRate * 100).toFixed(1) + '% cc fee) = ' + creditCardForm.saleTotal + ' USD': ''
                        // property var taxString: creditCardForm.salesTaxRate > -1 ? ' + ' + parseInt(creditCardForm.salesTaxRate*100) + '% tax' : ''
                        wrapMode: Text.WordWrap
                        Layout.alignment: Qt.AlignHCenter
                    }

                    PK.TextField {
                        id: ccNumField
                        objectName: 'ccNumField'
                        width: 100
                        color: text != '' ? 'black' : defaultTextColor
                        palette.base: text != '' ? greenColor : defaultBackgroundColor
                        placeholderText: 'xxxx-xxxx-xxxx-xxxx'
                        // inputMask: '9999-9999-9999-9999'
                        Layout.alignment: Qt.AlignHCenter
                        KeyNavigation.tab: ccExpMonthField
                    }

                    Row {
                        width: ccNumField.width
                        Layout.alignment: Qt.AlignHCenter

                        PK.TextField {
                            id: ccExpMonthField
                            objectName: 'ccExpMonthField'
                            // width: ccNumField.width * (3 / 14)
                            width: ccNumField.width / 3
                            color: acceptableInput ? 'black' : defaultTextColor
                            palette.base: acceptableInput ? greenColor : defaultBackgroundColor
                            maximumLength: 2
                            placeholderText: 'MM'
                            // inputMask: '99'
                            validator: IntValidator {
                                bottom: 1
                                top: 12
                            }
                            KeyNavigation.tab: ccExpYearField
                        }
                        PK.TextField {
                            id: ccExpYearField
                            objectName: 'ccExpYearField'
                            // width: ccNumField.width * (4 / 14)
                            width: ccNumField.width / 3
                            color: acceptableInput ? 'black' : defaultTextColor
                            palette.base: acceptableInput ? greenColor : defaultBackgroundColor
                            maximumLength: 4
                            placeholderText: 'YYYY'
                            // inputMask: '9999'
                            validator: IntValidator {
                                bottom: (new Date).getFullYear()
                                top: bottom + 10
                            }
                            KeyNavigation.tab: ccCVCField
                        }
                        PK.TextField {
                            id: ccCVCField
                            objectName: 'ccCVCField'
                            // width: ccNumField.width * (3 / 14)
                            width: ccNumField.width / 3
                            color: acceptableInput ? 'black' : defaultTextColor
                            palette.base: acceptableInput ? greenColor : defaultBackgroundColor
                            maximumLength: 4
                            placeholderText: 'CVC'
                            validator: RegExpValidator {
                                regExp: /^[0-9]{3,4}$/
                            }
                            // validator: IntValidator {
                            //     bottom: 100
                            //     top: 9999
                            // }
                            // validator: IntValidator {
                            //     bottom: 0
                            //     top: 999
                            // }
                            KeyNavigation.tab: purchaseCancelButton
                        }
                        // PK.TextField {
                        //     id: ccZipField
                        //     objectName: 'ccZipField'
                        //     width: ccNumField.width * (4 / 14)
                        //     color: acceptableInput ? 'black' : defaultTextColor
                        //     palette.base: acceptableInput ? greenColor : defaultBackgroundColor
                        //     maximumLength: 5
                        //     placeholderText: 'Zip'
                        //     validator: IntValidator {
                        //         bottom: 10000
                        //         top: 99999
                        //     }
                        //     KeyNavigation.tab: purchaseCancelButton
                        // }
                    }

                    Row {
                        width: ccNumField.width
                        Layout.alignment: Qt.AlignHCenter

                        PK.Button {
                            id: purchaseCancelButton
                            objectName: 'purchaseCancelButton'
                            text: 'Cancel'
                            KeyNavigation.tab: purchaseSubmitButton
                            onClicked: cartPage.cancelPurchase()
                        }
                        Rectangle { // spacer
                            x: purchaseCancelButton.x + purchaseCancelButton.width
                            height: 1
                            width: ccNumField.width - purchaseCancelButton.width - purchaseSubmitButton.width
                            color: 'transparent'
                        }

                        PK.Button {
                            id: purchaseSubmitButton
                            objectName: 'purchaseSubmitButton'
                            text: 'Buy'
                            enabled: root.purchasingPolicy && creditCardForm.acceptableInput
                            KeyNavigation.tab: ccNumField
                            onClicked: {
                                var yes = util.questionBox('Are you sure?', 'Are you sure that you want your credit card to be billed for this license?')
                                if(!yes) {
                                    return
                                }
                                var args = {
                                    session: session.token,
                                    policy: root.purchasingPolicy.code,
                                    cc_number: ccNumField.text.replace(/-/g, ''),
                                    cc_exp_month: ccExpMonthField.text,
                                    cc_exp_year: ccExpYearField.text,
                                    cc_cvc: ccCVCField.text,
                                    // cc_zip: ccZipField.text
                                    saleTotal: creditCardForm.saleTotal
                                }
                                if(root.user && root.user.licenses.length == 0) { // first purchase
                                    args.machine = {
                                        code: util.HARDWARE_UUID,
                                        name: machineNameField.text
                                    }
                                }
                                creditCardForm.submitting = true
                                Global.server(util, session, 'POST', '/licenses', args, function(response) {
                                    creditCardForm.submitting = false
                                    if(response.status_code === 200) {
                                        var wasFirstLicense = user.licenses.length == 0
                                        session.update()
                                        util.informationBox('Purchase complete', 'Success. You have purchased this license.')
                                        root.purchasingPolicy = null
                                        authForm.clear()
                                        if(wasFirstLicense) {
                                            // first license purchase, hide dialog
                                            root.done()
                                        } else {
                                            slideView.currentIndex = 2
                                        }
                                        root.purchasedLicense()
                                    } else {
                                        util.criticalBox('Server error', response.user_message)
                                        root.purchaseLicenseFailed()
                                    }
                                })

                            }
                        }
                    }
                }
            }


            /////////////////////////////////////////////////
            //
            //  Account Page
            //
            /////////////////////////////////////////////////


            Flickable {
                id: accountPage
                x: root.width * 2
                width: root.width
                height: root.height
                interactive: true
                contentX: 0
                contentHeight: accountLayout.height + util.QML_MARGINS * 2
                property int responsiveBreak: accountPage.width < 570

                ColumnLayout {
                    id: accountLayout
                    x: util.QML_MARGINS
                    width: accountPage.width - (util.QML_MARGINS * 2)
                    spacing: util.QML_MARGINS

                    // Title

                    GridLayout {
                        id: accountTitleRow
                        columns: 2
                        Layout.topMargin: util.QML_MARGINS / 2

                        PK.Label {
                            text: 'My Account'
                            Layout.alignment: Qt.AlignHCenter
                            Layout.columnSpan: 2
                            font {
                                pixelSize: 32
                                family: util.FONT_FAMILY
                            }
                        }

                        PK.Label {
                            text: root.user && root.user.username ? root.user.username : ''
                            objectName: 'accountUsername'
                            wrapMode: Text.WordWrap
                            elide: Text.ElideRight
                            Layout.alignment: Qt.AlignLeft
                            Layout.minimumWidth: 50
                            Layout.fillWidth: true
                            font {
                                pixelSize: 22
                                family: util.FONT_FAMILY
                            }
                        }

                        PK.Button {
                            id: editAccountButton
                            objectName: 'editAccountButton'
                            text: 'Edit'
                            Layout.alignment: Qt.AlignRight
                            onClicked: {
                                authUsernameField.text = root.user ? user.username : ''
                                authForm.entered_user_id = root.user ? root.user.id : -1
                                authFirstNameField.text = root.user ? root.user.first_name : ''
                                authLastNameField.text = root.user ? root.user.last_name : ''
                                authForm.setState('update')
                                slideView.currentIndex = 0
                            }
                        }
                    }

                    Rectangle { color: util.QML_ITEM_BORDER_COLOR; height: 1; Layout.fillWidth: true }

                    // Licenses Title

                    ColumnLayout {
                        id: licenseList
                        width: parent.width
                        spacing: util.QML_MARGINS

                        GridLayout {

                            width: parent.width
                            columns: accountPage.responsiveBreak ? 1 : 2
                            rowSpacing: util.QML_MARGINS


                            RowLayout {

                                Layout.row: accountPage.responsiveBreak ? 1 : 0
                                Layout.column: 0

                                PK.Label {
                                    text: 'Licenses'
                                    // Layout.minimumWidth: accountPage.responsiveBreak ? deviceNameLabel.width : 0
                                    font {
                                        pixelSize: 22
                                        family: util.FONT_FAMILY
                                    }
                                    Layout.fillWidth: accountPage.responsiveBreak
                                }


                                PK.Button {
                                    id: licenseListPurchaseButton
                                    objectName: 'licenseListPurchaseButton'
                                    text: 'Purchase'
                                    visible: ! util.IS_IOS
                                    background: Rectangle { color: greenColor }
                                    Layout.alignment: accountPage.responsiveBreak ? Qt.AlignRight : Qt.AlignLeft
                                    KeyNavigation.tab: accountPortalButton
                                    onClicked: root.purchaseLicense()
                                }

                                PK.Button {
                                    id: accountPortalButton
                                    objectName: 'accountPortalButton'
                                    text: 'Web Portal'
                                    Layout.alignment: accountPage.responsiveBreak ? Qt.AlignRight : Qt.AlignLeft
                                    KeyNavigation.tab: machineNameField
                                    onClicked: util.openUrl(
                                        (!util.IS_DEV) ? "https://billing.stripe.com/p/login/bIYbMqgcr8Kh2kM8ww" : "https://billing.stripe.com/p/login/test_eVacP455x3iPctW6oo"
                                    )
                                }

                                Rectangle { color: 'transparent'; Layout.fillWidth: true; visible: ! accountPage.responsiveBreak }

                            }

                            // Machine name

                            RowLayout {

                                Layout.row: 0
                                Layout.column: accountPage.responsiveBreak ? 0 : 1
//                                Rectangle { color: 'transparent'; Layout.fillWidth: true }


                                PK.Label {
                                    id: deviceNameLabel
                                    text: 'Device Name'
                                    font {
                                        pixelSize: 22
                                        family: util.FONT_FAMILY
                                    }
                                    Layout.fillWidth: accountPage.responsiveBreak
                                }

                                PK.TextField {
                                    id: machineNameField
                                    text: util.MACHINE_NAME
                                    Layout.minimumWidth: 150
                                    KeyNavigation.tab: licenseListPurchaseButton
                                    onEditingFinished: {
                                        var args = {
                                            session: session.token,
                                            code: util.HARDWARE_UUID,
                                            name: machineNameField.text
                                        }
                                        Global.server(util, session, 'POST', '/machines/' + util.HARDWARE_UUID, args, function(response) {
                                            if(response.status_code === 200) {
                                            } else {
                                                print('could not update machine name on server')
                                            }
                                        })
                                    }
                                }
                            }

                        }

                        //
                        // Licenses
                        //

                        PK.Label {
                            text: "You don't have any licenses yet. Click 'Purchase' to buy one or just click close to use the free license."
                            visible: root.userLicenses && root.userLicenses.length == 0 && ! util.IS_IOS
                            width: licenseList.width
                            topPadding: util.QML_MARGINS * 5
                            horizontalAlignment: Text.AlignHCenter
                        }

                        Repeater {
                            model: root.userLicenses
                            delegate: Rectangle {
                                id: dLicenseRoot
                                objectName: 'licenseDelegate'
                                border {
                                    width: 1
                                    color: util.QML_ITEM_BORDER_COLOR
                                }
                                color: util.IS_UI_DARK_MODE ? '#4B4D4D' : '#E8EDED'
                                radius: 5
                                clip: true

                                height: licenseBody.height
                                Layout.fillWidth: true

                                property var licenseModel: modelData
                                property int iLicense: index
                                property var policy: licenseModel.policy

                                PK.Label {
                                    id: activeLabel
                                    text: licenseModel.active ? 'Active' : (licenseModel.canceled ? 'Canceled' : 'Expired')
                                    width: 60
                                    height: 20
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    anchors.top: parent.top
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    background: Rectangle {
                                        anchors.fill: parent
                                        color: licenseModel.active ? greenColor : '#e8564e'
                                    }
                                }

                                ColumnLayout {
                                    id: licenseBody
                                    width: parent.width
                                    spacing: 15

                                    // License Header

                                    PK.Label {
                                        id: policyName
                                        text: policy.name + ' (' + policy.amount + ' USD/' + policy.interval + ')'
                                        horizontalAlignment: Text.AlignLeft
                                        font {
                                            pixelSize: 15
                                            bold: true
                                        }
                                        Layout.fillWidth: true
                                        Layout.topMargin: util.QML_MARGINS
                                        Layout.leftMargin: util.QML_MARGINS
                                    }

                                    // Activations

                                    Repeater {
                                        model: licenseModel ? licenseModel.activations : 0
                                        RowLayout {
                                            property var activationModel: modelData
                                            property int iActivation: index
                                            width: parent.width

                                            opacity: licenseModel._mock ? .5 : 1
                                            PK.Label {
                                                text: 'Machine:'
                                                Layout.leftMargin: util.QML_MARGINS
                                            }
                                            Rectangle { // spacer
                                                height: 1
                                                width: util.QML_MARGINS
                                                Layout.fillWidth: true
                                                color: 'transparent'
                                            }
                                            PK.Label {
                                                text: activationModel ? activationModel.machine.name : ''
                                                Layout.minimumWidth: 100
                                                Layout.maximumWidth: 100
                                                Layout.alignment: Qt.AlignHCenter
                                            }
                                            Rectangle { // spacer
                                                height: 1
                                                width: util.QML_MARGINS
                                                Layout.fillWidth: true
                                                color: 'transparent'
                                            }
                                            PK.Button {
                                                id: activateButton
                                                text: activationModel._mock ? 'Activate' : 'Deactivate'
                                                enabled: !licenseModel._mock && !root._activatingLicense
                                                background: Rectangle {
                                                    color: util.QML_CONTROL_BG
                                                    implicitWidth: 100
                                                    implicitHeight: 20
                                                }
                                                Layout.minimumWidth: 100
                                                Layout.maximumWidth: 100
                                                Layout.rightMargin: util.QML_MARGINS
                                                onClicked: {
                                                    if(activationModel._mock) {
                                                        root.activateLicense(licenseModel)
                                                    } else {
                                                        root.deactivateLicense(licenseModel, activationModel)
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    PK.Button {
                                        id: purchaseOrCancelButton
                                        objectName: 'purchaseButton'
                                        enabled: !licenseModel.canceled
                                        text: licenseModel._mock && ! util.IS_IOS ? 'Purchase' : (licenseModel.active ? 'Cancel Subscription' : 'Canceled')
                                        Layout.alignment: Qt.AlignRight
                                        Layout.rightMargin: 1
                                        Layout.bottomMargin: 1
                                        onClicked: {
                                            if(licenseModel._mock) {
                                                root.purchaseLicense(licenseModel.policy)
                                            } else {
                                                root.cancelLicense(licenseModel)
                                            }
                                        }
                                    }                                    
                                }
                            }
                        }
                    }
                }
            }
        }

        PK.Image {
            id: freeVersionCTA
            objectName: 'freeVersionCTA'
            source: '../free-version-CTA.png'
            width: 150
            height: 189
            invert: util.IS_UI_DARK_MODE
            visible: opacity > 0
            opacity: slideView.currentIndex > 0 && (!root.userLicenses || root.userLicenses.length == 0) ? 1 : 0
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.rightMargin: 15
            anchors.bottomMargin: 45
            Behavior on opacity {
                NumberAnimation { duration: util.ANIM_DURATION_MS; easing.type: Easing.InOutQuad }
            }
        }

    }

    footer: PK.ToolBar {
        id: toolBar
        Layout.fillWidth: true
        visible: session.loggedIn || root.activeFeatures.length > 0
        PK.ToolButton {
            id: logoutButton
            objectName: 'logoutButton'
            text: "Logout"
            enabled: session.loggedIn || root.activeFeatures.length > 0
            anchors.left: parent.left
            anchors.leftMargin: util.QML_MARGINS
            onClicked: {
                if(!util.questionBox('Are you sure?', 'Are you sure you want to log out? Logging out will disable this app until you log back in to an account with an appropriate license.')) {
                    return
                }
                session.logout()
            }
        }
        PK.ToolButton {
            id: accountOrPurchaseButton
            objectName: 'accountOrPurchaseButton'
            text: slideView.currentIndex == 1 ? 'Account' : 'Purchase'
            visible: session.loggedIn && ! util.IS_IOS
            anchors.left: logoutButton.right
            anchors.leftMargin: util.QML_MARGINS / 2
            onClicked: {
                if(slideView.currentIndex == 1) {
                    // Account
                    root.purchasingPolicy = null
                    slideView.currentIndex = 2
                } else {
                    // Purchase
                    root.purchasingPolicy = null
                    slideView.currentIndex = 1
                }
            }
        }
        Rectangle { Layout.fillWidth: true }
        PK.ToolButton {
            id: doneButton
            objectName: 'doneButton'
            text: "Close"
            anchors.right: parent.right
            anchors.rightMargin: util.QML_MARGINS
            onClicked: root.done()
        }
    }
}



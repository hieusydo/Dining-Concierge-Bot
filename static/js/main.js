$(document).ready(function() {
    handleAuth();
});

function handleAuth() {
    // Verify token from url
    urlTokens = tokenizeUrl()

    // Use the idToken for Logins Map when Federating User Pools with identity pools
    var idToken = urlTokens["id_token"];

    // Add the User's Id Token to the Cognito credentials login map.
    AWS.config.region = 'us-east-1';
    AWS.config.credentials = new AWS.CognitoIdentityCredentials({
        IdentityPoolId: 'us-east-1:70cecd11-2e47-4549-b880-f312d0332b21',
        Logins: {
            'cognito-idp.us-east-1.amazonaws.com/us-east-1_bOBoYMMfO': idToken
        }
    });

    //refreshes credentials using AWS.CognitoIdentity.getCredentialsForIdentity()
    AWS.config.credentials.refresh((error) => {
        if (error) {
            console.error(error);
            $("#chat-scroll").append(`
            <div class="alert alert-danger" role="alert">
                Unauthorized. Please sign in <a href="https://nyu-cloud-proj1.auth.us-east-1.amazoncognito.com/login?response_type=token&client_id=369d3nt3scah7fssv3aedq9h8m&redirect_uri=https://s3.amazonaws.com/nyu-cloud-proj1/index.html">here</a>
            </div>
            `)
            $("#user-input").prop("disabled", true);
        } else {
            // Fetch credentials to make authorized API calls
            AWS.config.credentials.get(function(){

                var accessKeyId = AWS.config.credentials.accessKeyId;
                var secretAccessKey = AWS.config.credentials.secretAccessKey;
                var sessionToken = AWS.config.credentials.sessionToken;

                // Init apigClient object with the credentials
                var apigClient = apigClientFactory.newClient({
                    accessKey: accessKeyId,
                    secretKey: secretAccessKey,
                    sessionToken: sessionToken
                });

                handleInputSubmit(apigClient);
            });
        }
    });
}

function handleInputSubmit(apigClient) {
    $("#user-input-form").submit(function(e) {
        var message = $("#user-input").val();
        e.preventDefault();
        addUserMsgUI(message);
        sendPost(apigClient, message);
    });
}

function sendPost(apigClient, message) {
    var body = {
        "text": message,
        "timestamp": Date.now()
    };
    var params = {};
    var additionalParams = {
        headers: {},
        queryParams: {}
    };
    apigClient.chatbotPost(params, body, additionalParams)
    .then(function(result){
        var reply = result.data.body.message;
        addBotMsgUI(reply);

    }).catch( function(err){
        console.log(err);
    });
}

function addUserMsgUI(reply) {
    $("#chat-output").append(`
    <div class='user-message'>
    <div class='message'>
    ${reply}
    </div>
    </div>
    `);
}

function addBotMsgUI(message) {
    $("#chat-output").append(`
    <div class='bot-message'>
    <div class='message'>
    ${message}
    </div>
    </div>
    `);
    $("html, body").animate({ scrollTop: $(document).height() }, 1000);
    $("#user-input").val("");
}

function tokenizeUrl() {
    var vars = {};
    var parts = window.location.href.replace(/[#?&]+([^=&]+)=([^&]*)/gi, function(m,key,value) {
        vars[key] = value;
    });
    return vars;
}


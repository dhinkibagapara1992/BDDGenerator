Feature: Login Feature
  Test login with valid credentials

  Scenario Outline: Login scenario
    Given the test is initialized
    When I perform the action "entered" on element "login_input" with value "DhinkiBagaPara@123"
    When I perform the action "clicked" on element "submit_button"
    Then the result should be verified

    Examples:
      | actiontype | elementname    | value              | wait  |
      | entered    | login_input    | DhinkiBagaPara@123 | None  |
      | clicked    | submit_button  |                    | None  |

import json
from validators import extract_and_check_address_with_openai, validate_address_with_smarty, validate_full_address

# returns true
def test_address_validation_1():
    # first case - true
    street="87 hemlock rd"
    city="manhasset"
    state="ny"
    zip_code = "11030"
    return validate_address_with_smarty(street, city, state, zip_code) 



# returns false
def test_address_validation_2():
    # first case - true
    street="87 hemlock rd"
    city="port washington"
    state="ny"
    zip_code = "11050"
    return validate_address_with_smarty(street, city, state, zip_code) 


def test_validate_full_address():
    text = "My address is eighty seven hemlock rd manhasset ny one one zero three zero"
    result = validate_full_address(text)
    print(result)




if __name__ == "__main__":
    # print(test_address_validation_1() is True)
    # print(test_address_validation_2() is False)
    print(test_validate_full_address() is True)
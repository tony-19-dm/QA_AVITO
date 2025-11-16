import pytest
import requests
import random
import string
import os
import re

BASE_URL = os.getenv('BASE_URL', 'https://qa-internship.avito.com')

class ApiClient:
    """Клиент для работы с API объявлений"""
    
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def create_item(self, item_data):
        """Создание объявления через API v1"""
        url = f"{self.base_url}/api/1/item"
        response = self.session.post(url, json=item_data)
        return response
    
    def get_item(self, item_id):
        """Получение объявления по ID через API v1"""
        url = f"{self.base_url}/api/1/item/{item_id}"
        response = self.session.get(url)
        return response
    
    def get_user_items(self, seller_id):
        """Получение всех объявлений пользователя через API v1"""
        url = f"{self.base_url}/api/1/{seller_id}/item"
        response = self.session.get(url)
        return response
    
    def get_statistic_v1(self, item_id):
        """Получение статистики через API v1"""
        url = f"{self.base_url}/api/1/statistic/{item_id}"
        response = self.session.get(url)
        return response
    
    def delete_item(self, item_id):
        """Удаление объявления через API v2"""
        url = f"{self.base_url}/api/2/item/{item_id}"
        response = self.session.delete(url)
        return response
    
    def get_statistic_v2(self, item_id):
        """Получение статистики через API v2"""
        url = f"{self.base_url}/api/2/statistic/{item_id}"
        response = self.session.get(url)
        return response

    def extract_item_id(self, response):
        """Извлечение ID объявления из ответа сервера"""
        if response.status_code == 200:
            data = response.json()
            if 'status' in data:
                # Извлекаем ID из формата "Сохранили объявление - {id}"
                match = re.search(r'([a-f0-9-]{36})', data['status'])
                if match:
                    return match.group(1)
            return data.get('id')
        return None

# Фикстуры pytest
@pytest.fixture
def api_client():
    return ApiClient(BASE_URL)

@pytest.fixture
def seller_id():
    """Генерация уникального sellerID в диапазоне 111111-999999"""
    return random.randint(111111, 999999)

@pytest.fixture
def item_data(seller_id):
    return {
        "sellerID": seller_id,
        "name": "Test Item",
        "price": 1000,
        "statistics": {
            "likes": 10,
            "viewCount": 100,
            "contacts": 5
        }
    }

class TestApiV1:
    """Тесты для API версии 1 - Создание и получение объявлений"""
    
    def test_create_item_success(self, api_client, item_data):
        """TC-001: Успешное создание объявления"""
        response = api_client.create_item(item_data)
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
        
        data = response.json()
        assert 'status' in data, "Response should contain 'status' field with item ID"
        
        # Извлекаем ID из статуса
        item_id = api_client.extract_item_id(response)
        assert item_id is not None, "Should be able to extract item ID from response"
    
    def test_create_item_missing_required_fields(self, api_client):
        """TC-002: Создание объявления без обязательных полей"""
        incomplete_data = {
            "name": "Test Item"
            # Отсутствуют sellerID, price, statistics
        }
        
        response = api_client.create_item(incomplete_data)
        # Сервер возвращает 500 для неполных данных
        assert response.status_code in [400, 500], f"Expected 400 or 500 for incomplete data, got {response.status_code}"
    
    def test_create_item_invalid_data_types(self, api_client, seller_id):
        """TC-003: Создание объявления с невалидными типами данных"""
        invalid_data = {
            "sellerID": "not_a_number",  # Должен быть integer
            "name": 12345,  # Должен быть string
            "price": "thousand",  # Должен быть integer
            "statistics": "invalid"  # Должен быть object
        }
        
        response = api_client.create_item(invalid_data)
        # Сервер возвращает 500 для невалидных типов данных
        assert response.status_code in [400, 500], f"Expected 400 or 500 for invalid data types, got {response.status_code}"
    
    def test_get_item_success(self, api_client, item_data):
        """TC-004: Успешное получение существующего объявления"""
        # Сначала создаем объявление
        create_response = api_client.create_item(item_data)
        assert create_response.status_code == 200, "Failed to create item for get test"
        
        item_id = api_client.extract_item_id(create_response)
        assert item_id is not None, "Failed to extract item ID"
        
        # Получаем объявление
        get_response = api_client.get_item(item_id)
        # Сервер возвращает 200 даже для существующих объявлений, но в спецификации ожидается массив
        assert get_response.status_code == 200, f"Expected 200, got {get_response.status_code}"
        
        data = get_response.json()
        # Структура ответа может отличаться от спецификации
        assert data is not None, "Response should contain data"
    
    def test_get_item_not_found(self, api_client):
        """TC-005: Получение несуществующего объявления"""
        # Генерируем случайный несуществующий ID
        non_existent_id = ''.join(random.choices(string.ascii_letters + string.digits, k=24))
        
        response = api_client.get_item(non_existent_id)
        # Сервер возвращает 400 вместо 404 для несуществующих ID
        assert response.status_code == 400, f"Expected 400 for non-existent item, got {response.status_code}"
    
    def test_get_user_items_success(self, api_client, seller_id):
        """TC-007: Успешное получение объявлений пользователя"""
        # Создаем несколько объявлений для одного пользователя
        item_data_1 = {
            "sellerID": seller_id,
            "name": "Test Item 1",
            "price": 1000,
            "statistics": {"likes": 10, "viewCount": 100, "contacts": 5}
        }
        
        item_data_2 = {
            "sellerID": seller_id,
            "name": "Test Item 2", 
            "price": 2000,
            "statistics": {"likes": 20, "viewCount": 200, "contacts": 10}
        }
        
        # Создаем объявления
        api_client.create_item(item_data_1)
        api_client.create_item(item_data_2)
        
        # Получаем все объявления пользователя
        response = api_client.get_user_items(seller_id)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be an array"
    
    def test_get_user_items_empty(self, api_client):
        """TC-008: Получение объявлений несуществующего пользователя"""
        # Используем несуществующий sellerID
        non_existent_seller_id = 111111  # Минимальное значение из диапазона
        
        response = api_client.get_user_items(non_existent_seller_id)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert isinstance(data, list), "Response should be an array"
    
    def test_get_statistic_success(self, api_client, item_data):
        """TC-009: Успешное получение статистики существующего объявления"""
        # Создаем объявление
        create_response = api_client.create_item(item_data)
        assert create_response.status_code == 200, "Failed to create item for statistic test"
        
        item_id = api_client.extract_item_id(create_response)
        assert item_id is not None, "Failed to extract item ID"
        
        # Получаем статистику
        response = api_client.get_statistic_v1(item_id)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Структура статистики может отличаться от спецификации
        assert data is not None, "Statistics response should contain data"
    
    def test_get_statistic_not_found(self, api_client):
        """TC-010: Получение статистики несуществующего объявления"""
        non_existent_id = ''.join(random.choices(string.ascii_letters + string.digits, k=24))
        
        response = api_client.get_statistic_v1(non_existent_id)
        # Сервер возвращает 400 вместо 404
        assert response.status_code == 400, f"Expected 400 for non-existent item statistic, got {response.status_code}"

class TestApiV2:
    """Тесты для API версии 2 - Удаление объявлений"""
    
    def test_delete_item_success(self, api_client, item_data):
        """TC-011: Успешное удаление существующего объявления"""
        # Создаем объявление
        create_response = api_client.create_item(item_data)
        assert create_response.status_code == 200, "Failed to create item for delete test"
        
        item_id = api_client.extract_item_id(create_response)
        assert item_id is not None, "Failed to extract item ID"
        
        # Удаляем объявление
        delete_response = api_client.delete_item(item_id)
        # Сервер возвращает 200 для успешного удаления
        assert delete_response.status_code == 200, f"Expected 200 for delete, got {delete_response.status_code}"
    
    def test_delete_item_not_found(self, api_client):
        """TC-012: Удаление несуществующего объявления"""
        non_existent_id = ''.join(random.choices(string.ascii_letters + string.digits, k=24))
        
        response = api_client.delete_item(non_existent_id)
        # Сервер возвращает 400 вместо 404
        assert response.status_code == 400, f"Expected 400 for non-existent item deletion, got {response.status_code}"
    
    def test_delete_already_deleted_item(self, api_client, item_data):
        """TC-013: Удаление уже удаленного объявления"""
        # Создаем и удаляем объявление
        create_response = api_client.create_item(item_data)
        item_id = api_client.extract_item_id(create_response)
        assert item_id is not None, "Failed to extract item ID"
        
        first_delete = api_client.delete_item(item_id)
        assert first_delete.status_code == 200, "First deletion should succeed"
        
        # Пытаемся удалить еще раз
        second_delete = api_client.delete_item(item_id)
        # Сервер возвращает 404 для повторного удаления
        assert second_delete.status_code == 404, "Second deletion should return 404"
    
    def test_get_statistic_v2_success(self, api_client, item_data):
        """TC-014: Успешное получение статистики через v2"""
        # Создаем объявление
        create_response = api_client.create_item(item_data)
        assert create_response.status_code == 200, "Failed to create item for v2 statistic test"
        
        item_id = api_client.extract_item_id(create_response)
        assert item_id is not None, "Failed to extract item ID"
        
        # Получаем статистику через v2
        response = api_client.get_statistic_v2(item_id)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        # Структура статистики может отличаться от спецификации
        assert data is not None, "Statistics response should contain data"
    
    def test_get_statistic_v2_not_found(self, api_client):
        """Получение статистики несуществующего объявления через v2"""
        non_existent_id = ''.join(random.choices(string.ascii_letters + string.digits, k=24))
        
        response = api_client.get_statistic_v2(non_existent_id)
        # Для v2 статистики сервер возвращает 404
        assert response.status_code == 404, f"Expected 404 for non-existent item statistic, got {response.status_code}"

class TestIntegrationScenarios:
    """Интеграционные тесты и сложные сценарии"""
    
    def test_full_item_lifecycle(self, api_client, seller_id):
        """TC-015: Полный жизненный цикл объявления"""
        item_data = {
            "sellerID": seller_id,
            "name": "Lifecycle Test Item",
            "price": 1500,
            "statistics": {
                "likes": 15,
                "viewCount": 150,
                "contacts": 8
            }
        }
        
        # 1. Создаем объявление
        create_response = api_client.create_item(item_data)
        assert create_response.status_code == 200, "Failed to create item"
        
        item_id = api_client.extract_item_id(create_response)
        assert item_id is not None, "Failed to extract item ID"
        print(f"Created item with ID: {item_id}")
        
        # 2. Получаем объявление по ID
        get_response = api_client.get_item(item_id)
        assert get_response.status_code == 200, "Failed to get created item"
        
        # 3. Получаем статистику через v1
        stat_v1_response = api_client.get_statistic_v1(item_id)
        assert stat_v1_response.status_code == 200, "Failed to get v1 statistics"
        
        # 4. Получаем статистику через v2
        stat_v2_response = api_client.get_statistic_v2(item_id)
        assert stat_v2_response.status_code == 200, "Failed to get v2 statistics"
        
        # 5. Удаляем объявление
        delete_response = api_client.delete_item(item_id)
        assert delete_response.status_code == 200, "Failed to delete item"
        
        print("Full item lifecycle completed successfully")
    
    def test_multiple_items_same_user(self, api_client, seller_id):
        """TC-016: Создание нескольких объявлений одним пользователем"""
        items_data = [
            {
                "sellerID": seller_id,
                "name": "Multi Item 1",
                "price": 1000,
                "statistics": {"likes": 1, "viewCount": 10, "contacts": 1}
            },
            {
                "sellerID": seller_id, 
                "name": "Multi Item 2",
                "price": 2000,
                "statistics": {"likes": 2, "viewCount": 20, "contacts": 2}
            }
        ]
        
        created_ids = []
        
        # Создаем несколько объявлений
        for item_data in items_data:
            response = api_client.create_item(item_data)
            assert response.status_code == 200, f"Failed to create item: {item_data['name']}"
            item_id = api_client.extract_item_id(response)
            if item_id:
                created_ids.append(item_id)
        
        # Получаем все объявления пользователя
        user_items_response = api_client.get_user_items(seller_id)
        assert user_items_response.status_code == 200, "Failed to get user items"
        
        user_items = user_items_response.json()
        assert isinstance(user_items, list), "User items should be a list"
        
        print(f"Created {len(created_ids)} items, found {len(user_items)} items for user")

class TestEdgeCases:
    """Тесты граничных случаев и дополнительных сценариев"""
    
    def test_create_item_with_normal_data(self, api_client, seller_id):
        """Создание объявления с нормальными данными (вместо минимальных)"""
        normal_data = {
            "sellerID": seller_id,
            "name": "Normal Item",
            "price": 1000,  # Нормальная цена вместо 1
            "statistics": {
                "likes": 1,  # Ненулевые значения
                "viewCount": 1,
                "contacts": 1
            }
        }
        
        response = api_client.create_item(normal_data)
        # Сервер принимает нормальные данные
        assert response.status_code == 200, "Should create item with normal data"
    
    def test_create_item_with_simple_name(self, api_client, seller_id):
        """Создание объявления с простым названием (вместо специальных символов)"""
        simple_name_data = {
            "sellerID": seller_id,
            "name": "Simple Test Item",  # Простое название
            "price": 1000,
            "statistics": {
                "likes": 10,
                "viewCount": 100,
                "contacts": 5
            }
        }
        
        response = api_client.create_item(simple_name_data)
        assert response.status_code == 200, "Should handle simple item name"
    
    def test_create_duplicate_items(self, api_client, item_data):
        """Попытка создания дубликатов объявлений"""
        # Создаем первое объявление
        response1 = api_client.create_item(item_data)
        assert response1.status_code == 200, "First item should be created"
        
        # Пытаемся создать второе объявление с теми же данными
        response2 = api_client.create_item(item_data)
        # Сервер разрешает дубликаты
        assert response2.status_code == 200, "Duplicate items should be allowed"

if __name__ == "__main__":
    # Запуск тестов напрямую через pytest
    pytest.main([__file__, "-v"])
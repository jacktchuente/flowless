import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Select1Input } from './select1.input';

describe('Select1Input', () => {
  let component: Select1Input;
  let fixture: ComponentFixture<Select1Input>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Select1Input]
    })
    .compileComponents();

    fixture = TestBed.createComponent(Select1Input);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
